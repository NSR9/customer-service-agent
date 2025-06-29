"""
FastAPI server for Customer Support Agent
"""
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import uvicorn
import uuid
from sqlalchemy.orm import Session, joinedload

# Import graph components
from graph import graph_app
from state import SupportAgentState
from langchain_core.messages import HumanMessage

# Import database components
from database.ticket_db import get_db, save_ticket_state, Ticket, TicketState
from database.data import ORDERS, SHIPMENTS, PRODUCTS, CUSTOMERS, INVENTORY

# Create FastAPI app
app = FastAPI(
    title="Customer Support Agent API",
    description="API for processing customer support tickets using LangGraph",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for request and response
class TicketRequest(BaseModel):
    ticket_id: str
    ticket_description: str
    customer_id: str
    received_date: datetime
    processed_date: Optional[datetime] = None

class TicketResponse(BaseModel):
    ticket_id: str
    status: str
    message: str
    problems: Optional[List[str]] = None
    policy_name: Optional[str] = None
    action_taken: Optional[str] = None
    customer_id: Optional[str] = None
    description: Optional[str] = None
    received_date: Optional[datetime] = None
    processed_date: Optional[datetime] = None
    messages: Optional[List[Dict[str, Any]]] = None

class TicketDetailResponse(TicketResponse):
    policy_desc: Optional[str] = None
    reason: Optional[str] = None
    reasoning: Optional[Dict[str, Any]] = None
    thought_process: Optional[List[Dict[str, Any]]] = None



#New Models

class TrackingHistoryResponse(BaseModel):
    tracking_id: str
    order_id: str
    status: str
    location: str
    timestamp: datetime

class OrderItem(BaseModel):
    product_id: str
    quantity: int
    unit_price: float
    total_price: float
 

class OrderResponse(BaseModel):
    order_id: str
    customer_id: str
    status: str
    items: List[OrderItem]
    total_amount: float

class CustomerResponse(BaseModel):
    customer_id: str
    name: str
    email: str
    phone: str
    address: str

class ProductResponse(BaseModel):
    product_id: str
    name: str
    description: str
    price: float
    category: str
    weight: float
    dimensions: Dict[str, float]

class InventoryResponse(BaseModel):
    product_id: str
    quantity: int
    warehouse_id: str
    location: str
    last_restock_date: datetime
    reorder_threshold: int
    reorder_quantity: int

# Process ticket in background
def process_ticket_task(ticket_data: Dict[str, Any], db: Session = Depends(get_db)):
    """
    Process a ticket using the LangGraph workflow and save results to database
    """
    try:
        # Create initial state with customer message
        initial_state = SupportAgentState(
            messages=[HumanMessage(content=ticket_data["description"])]
        )
        
        # Execute the graph
        final_state = graph_app.invoke(initial_state)
        
        # Log the completion of the workflow
        print(f"Workflow completed for ticket {ticket_data['ticket_id']}")
        print(f"Final state: {final_state}`")
        
        # Handle different state object types
        # If final_state is a dict-like object (AddableValuesDict)
        if hasattr(final_state, 'get'):
            # Extract relevant fields safely using get() method
            problems = final_state.get('problems', [])
            actions = final_state.get('actions', None)
            action_taken = actions[0] if isinstance(actions, list) and actions else None
            messages = final_state.get('messages', [])
            print(f"Problems identified: {problems}")
            print(f"Action taken: {action_taken}")
        else:
            # Try to access attributes directly if it's an object with attributes
            problems = getattr(final_state, 'problems', []) if hasattr(final_state, 'problems') else []
            action_taken = getattr(final_state, 'action_taken', None) if hasattr(final_state, 'action_taken') else None
            messages = getattr(final_state, 'messages', []) if hasattr(final_state, 'messages') else []
            print(f"Problems identified: {problems}")
            print(f"Action taken: {action_taken}")
        
        # Save ticket and state to database
        print(f"Saving ticket and state to database: {ticket_data}, {final_state}")
        try:
            save_ticket_state(ticket_data, final_state, db)
        except Exception as e:
            print(f"Error saving ticket state: {str(e)}")
            # Continue execution even if saving to DB fails
        
        # Return the final state
        return final_state
    except Exception as e:
        print(f"Error processing ticket {ticket_data['ticket_id']}: {str(e)}")
        # Re-raise the exception to be handled by the caller
        raise e

@app.post("/tickets", response_model=TicketResponse)
async def create_ticket(
    ticket: TicketRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Create a new support ticket and process it asynchronously
    """
    # Debug logging
    print("\n=== RECEIVED TICKET REQUEST ===")
    print(f"ticket_id: {ticket.ticket_id}")
    print(f"ticket_description: {ticket.ticket_description[:50]}...")
    print(f"customer_id: {ticket.customer_id}")
    print(f"received_date: {ticket.received_date}")
    print("===============================\n")
    try:
        # Check if ticket already exists
        existing_ticket = db.query(Ticket).filter(Ticket.ticket_id == ticket.ticket_id).first()
        if existing_ticket:
            return {
                "ticket_id": ticket.ticket_id,
                "status": "error",
                "message": f"Ticket with ID {ticket.ticket_id} already exists"
            }
            
        # Create a new ticket in the database with 'processing' status
        new_ticket = Ticket(
            ticket_id=ticket.ticket_id,
            customer_id=ticket.customer_id,
            description=ticket.ticket_description,
            received_date=ticket.received_date,
            status="processing"
        )
        db.add(new_ticket)
        db.commit()
        print(f"New ticket created: {new_ticket}")
        
        # Prepare ticket data for background processing
        ticket_data = {
            "ticket_id": ticket.ticket_id,
            "customer_id": ticket.customer_id,
            "description": ticket.ticket_description,
            "received_date": ticket.received_date,
            "status": "processing"
        }
        
        # Add ticket processing to background tasks
        background_tasks.add_task(process_ticket_task, ticket_data, db)
        
        return {
            "ticket_id": ticket.ticket_id,
            "status": "processing",
            "message": "Ticket received and being processed. Check status later using GET /tickets/{ticket_id}"
        }
    except Exception as e:
        db.rollback()
        return {
            "ticket_id": ticket.ticket_id,
            "status": "error",
            "message": f"Error creating ticket: {str(e)}"
        }

@app.get("/tickets/{ticket_id}", response_model=TicketDetailResponse)
async def get_ticket(ticket_id: str, db: Session = Depends(get_db)):
    """
    Get ticket details by ticket ID
    """
    # Query the database for the ticket
    ticket = db.query(Ticket).filter(Ticket.ticket_id == ticket_id).first()
    
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    try:
        # Use a specific query that only selects columns that exist in the database
        ticket_state = db.query(
            TicketState.problems,
            TicketState.policy_name,
            TicketState.policy_desc,
            TicketState.action_taken,
            TicketState.reason,
            TicketState.reasoning,
            TicketState.thought_process,
            TicketState.messages
        ).filter(TicketState.ticket_id == ticket.id).first()
        
        if not ticket_state:
            return {
                "ticket_id": ticket.ticket_id,
                "status": ticket.status,
                "message": "Ticket found but processing not complete",
                "customer_id": ticket.customer_id,
                "description": ticket.description,
                "received_date": ticket.received_date,
                "processed_date": ticket.processed_date,
                "messages": []  # Include empty messages array
            }
        
        # Return full ticket details with state
        response = {
            "ticket_id": ticket.ticket_id,
            "status": ticket.status,
            "message": "Ticket processing complete",
            "customer_id": ticket.customer_id,
            "description": ticket.description,
            "received_date": ticket.received_date,
            "processed_date": ticket.processed_date,
            "problems": ticket_state.problems,
            "policy_name": ticket_state.policy_name,
            "policy_desc": ticket_state.policy_desc,
            "action_taken": ticket_state.action_taken,
            "reason": ticket_state.reason,
            "reasoning": ticket_state.reasoning,
            "thought_process": ticket_state.thought_process,
            "messages": ticket_state.messages if ticket_state.messages else []
        }
        return response
    except Exception as e:
        print(f"Error accessing ticket state data: {str(e)}")
        db.rollback()  # Roll back the transaction to avoid cascading errors
        
        # Return basic ticket info without state data
        return {
            "ticket_id": ticket.ticket_id,
            "status": ticket.status,
            "message": f"Error retrieving ticket state: {str(e)}",
            "customer_id": ticket.customer_id,
            "description": ticket.description,
            "received_date": ticket.received_date,
            "processed_date": ticket.processed_date,
            "messages": []  # Include empty messages array
        }

@app.get("/tickets", response_model=List[TicketResponse])
async def list_tickets(db: Session = Depends(get_db)):
    """
    List all tickets
    """
    tickets = db.query(Ticket).all()
    
    result = []
    for ticket in tickets:
        # print(ticket.processed_date)
        ticket_data = {
            "ticket_id": ticket.ticket_id,
            "status": ticket.status,
            "message": "Ticket found",
            "received_date": ticket.received_date,
            "processed_date": ticket.processed_date,
            "description": ticket.description,
            "customer_id": ticket.customer_id
        }
        
        try:
            # Use a specific query that only selects columns that exist in the database
            ticket_state = db.query(
                TicketState.problems,
                TicketState.policy_name,
                TicketState.policy_desc,
                TicketState.action_taken,
                TicketState.messages
            ).filter(TicketState.ticket_id == ticket.id).first()
            
            if ticket_state:
                ticket_data.update({
                    "problems": ticket_state.problems,
                    "policy_name": f"{ticket_state.policy_name}",
                    "policy_desc": f"{ticket_state.policy_desc}",
                    "action_taken": ticket_state.action_taken,
                    "messages": ticket_state.messages if ticket_state.messages else []                })
        except Exception as e:
            print(f"Error accessing ticket state data: {str(e)}")
            # Continue without state data
            db.rollback()  # Roll back the transaction to avoid cascading errors
            ticket_data["messages"] = []  # Ensure messages field is present even on error
        
        result.append(ticket_data)
    
    return result


@app.get("/tracking_history", response_model=List[TrackingHistoryResponse])
async def get_tracking_history(order_id: Optional[str] = None, db: Session = Depends(get_db)):
    """
    Get tracking history with optional filtering by order_id
    """
    tracking_history = []
    
    for shipment_id, shipment in SHIPMENTS.items():
        if order_id and shipment.order_id != order_id:
            continue
            
        for event in shipment.tracking_history:
            tracking_history.append(TrackingHistoryResponse(
                tracking_id=shipment.tracking_number,
                order_id=shipment.order_id,
                status=event.status.value,
                location=event.location,
                timestamp=event.timestamp
            ))
    
    return tracking_history

@app.get("/tracking_history/{order_id}", response_model=List[TrackingHistoryResponse])
async def get_tracking_history_by_order(order_id: str, db: Session = Depends(get_db)):
    """
    Get tracking history for a specific order
    """
    tracking_history = []
    
    for shipment_id, shipment in SHIPMENTS.items():
        if shipment.order_id == order_id:
            for event in shipment.tracking_history:
                tracking_history.append(TrackingHistoryResponse(
                    tracking_id=shipment.tracking_number,
                    order_id=shipment.order_id,
                    status=event.status.value,
                    location=event.location,
                    timestamp=event.timestamp
                ))
    
    if not tracking_history:
        raise HTTPException(status_code=404, detail=f"No tracking history found for order {order_id}")
    
    return tracking_history

@app.get("/orders", response_model=List[OrderResponse])
async def get_orders(customer_id: Optional[str] = None, status: Optional[str] = None, db: Session = Depends(get_db)):
    """
    Get all orders with optional filtering by customer_id and status
    """
    filtered_orders = []
    
    for order_id, order in ORDERS.items():
        # Apply filters if provided
        if customer_id and order.customer_id != customer_id:
            continue
        if status and order.status.value != status:
            continue
            
        # Convert order items to Pydantic model format
        items = [
            OrderItem(
                product_id=item.product_id,
                quantity=item.quantity,
                unit_price=item.unit_price,
                total_price=item.total_price
            ) for item in order.items
        ]
        
        filtered_orders.append(OrderResponse(
            order_id=order.id,
            customer_id=order.customer_id,
            status=order.status.value,
            items=items,
            total_amount=order.total_amount
        ))
    
    return filtered_orders

@app.get("/orders/{order_id}", response_model=OrderResponse)
async def get_order_by_id(order_id: str, db: Session = Depends(get_db)):
    """
    Get a specific order by ID
    """
    if order_id not in ORDERS:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
    
    order = ORDERS[order_id]
    
    # Convert order items to Pydantic model format
    items = [
        OrderItem(
            product_id=item.product_id,
            quantity=item.quantity,
            unit_price=item.unit_price,
            total_price=item.total_price
        ) for item in order.items
    ]
    
    return OrderResponse(
        order_id=order.id,
        customer_id=order.customer_id,
        status=order.status.value,
        items=items,
        total_amount=order.total_amount
    )

@app.get("/customers", response_model=List[CustomerResponse])
async def get_customers(search: Optional[str] = None, db: Session = Depends(get_db)):
    """
    Get all customers with optional search by name or email
    """
    filtered_customers = []
    
    for customer_id, customer in CUSTOMERS.items():
        # Apply search filter if provided
        if search:
            search_lower = search.lower()
            if (search_lower not in customer.name.lower() and 
                search_lower not in customer.email.lower()):
                continue
        
        filtered_customers.append(CustomerResponse(
            customer_id=customer.id,
            name=customer.name,
            email=customer.email,
            phone=customer.phone,
            address=customer.address.get("street", "") + ", " + 
                   customer.address.get("city", "") + ", " +
                   customer.address.get("state", "") + " " +
                   customer.address.get("zip", "")
        ))
    
    return filtered_customers

@app.get("/customers/{customer_id}", response_model=CustomerResponse)
async def get_customer_by_id(customer_id: str, db: Session = Depends(get_db)):
    """
    Get a specific customer by ID
    """
    if customer_id not in CUSTOMERS:
        raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found")
    
    customer = CUSTOMERS[customer_id]
    
    return CustomerResponse(
        customer_id=customer.id,
        name=customer.name,
        email=customer.email,
        phone=customer.phone,
        address=customer.address.get("street", "") + ", " + 
               customer.address.get("city", "") + ", " +
               customer.address.get("state", "") + " " +
               customer.address.get("zip", "")
    )

@app.get("/products", response_model=List[ProductResponse])
async def get_products(category: Optional[str] = None, search: Optional[str] = None, db: Session = Depends(get_db)):
    """
    Get all products with optional filtering by category and search term
    """
    filtered_products = []
    
    for product_id, product in PRODUCTS.items():
        # Apply category filter if provided
        if category and product.category.value != category:
            continue
        
        # Apply search filter if provided
        if search:
            search_lower = search.lower()
            if (search_lower not in product.name.lower() and 
                search_lower not in product.description.lower()):
                continue
        
        filtered_products.append(ProductResponse(
            product_id=product.id,
            name=product.name,
            description=product.description,
            price=product.price,
            category=product.category.value,
            weight=product.weight,
            dimensions=product.dimensions
        ))
    
    return filtered_products

@app.get("/products/{product_id}", response_model=ProductResponse)
async def get_product_by_id(product_id: str, db: Session = Depends(get_db)):
    """
    Get a specific product by ID
    """
    if product_id not in PRODUCTS:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")
    
    product = PRODUCTS[product_id]
    
    return ProductResponse(
        product_id=product.id,
        name=product.name,
        description=product.description,
        price=product.price,
        category=product.category.value,
        weight=product.weight,
        dimensions=product.dimensions
    )

@app.get("/inventory", response_model=List[InventoryResponse])
async def get_inventory(warehouse_id: Optional[str] = None, low_stock: Optional[bool] = None, db: Session = Depends(get_db)):
    """
    Get all inventory with optional filtering by warehouse_id and low stock status
    """
    filtered_inventory = []
    
    for product_id, inventory in INVENTORY.items():
        # Apply warehouse filter if provided
        if warehouse_id and inventory.warehouse_id != warehouse_id:
            continue
        
        # Apply low stock filter if provided
        if low_stock is not None:
            is_low = inventory.quantity <= inventory.reorder_threshold
            if low_stock != is_low:
                continue
        
        filtered_inventory.append(InventoryResponse(
            product_id=inventory.product_id,
            quantity=inventory.quantity,
            warehouse_id=inventory.warehouse_id,
            location=inventory.location,
            last_restock_date=inventory.last_restock_date,
            reorder_threshold=inventory.reorder_threshold,
            reorder_quantity=inventory.reorder_quantity
        ))
    
    return filtered_inventory

@app.get("/inventory/{product_id}", response_model=InventoryResponse)
async def get_inventory_by_product(product_id: str, db: Session = Depends(get_db)):
    """
    Get inventory for a specific product
    """
    if product_id not in INVENTORY:
        raise HTTPException(status_code=404, detail=f"Inventory for product {product_id} not found")
    
    inventory = INVENTORY[product_id]
    
    return InventoryResponse(
        product_id=inventory.product_id,
        quantity=inventory.quantity,
        warehouse_id=inventory.warehouse_id,
        location=inventory.location,
        last_restock_date=inventory.last_restock_date,
        reorder_threshold=inventory.reorder_threshold,
        reorder_quantity=inventory.reorder_quantity
    )

@app.get("/dashboard/summary")
async def get_dashboard_summary(db: Session = Depends(get_db)):
    """
    Get summary statistics for the support dashboard
    """
    # Get ticket statistics from database
    total_tickets = db.query(Ticket).count()
    resolved_tickets = db.query(Ticket).filter(Ticket.status == "resolved").count()
    pending_tickets = db.query(Ticket).filter(Ticket.status == "new").count()
    in_progress_tickets = db.query(Ticket).filter(Ticket.status == "processing").count()
    
    # Calculate percentages (mock data for now)
    total_change_pct = 12  # +12% vs last week
    resolved_change_pct = 24  # +24% vs last week
    pending_change_pct = 0  # 0% vs last week
    in_progress_change_pct = 45  # +45% vs last week
    
    # Get AI analysis info
    ai_tickets_analyzed = total_tickets
    
    # Get priority queue info
    urgent_tickets = db.query(Ticket).filter(Ticket.status == "new").count()
    
    # Get auto resolution info
    auto_resolved_count = resolved_tickets
    auto_resolution_pct = 100 if total_tickets > 0 else 0
    
    return {
        "total_tickets": {
            "count": total_tickets,
            "change_pct": total_change_pct
        },
        "resolved_tickets": {
            "count": resolved_tickets,
            "change_pct": resolved_change_pct
        },
        "pending_tickets": {
            "count": pending_tickets,
            "change_pct": pending_change_pct
        },
        "in_progress_tickets": {
            "count": in_progress_tickets,
            "change_pct": in_progress_change_pct
        },
        "ai_analysis": {
            "tickets_analyzed": ai_tickets_analyzed,
            "message": "AI is analyzing incoming tickets for sentiment and urgency."
        },
        "priority_queue": {
            "urgent_tickets": urgent_tickets,
            "message": f"{'No' if urgent_tickets == 0 else urgent_tickets} tickets currently marked as urgent."
        },
        "auto_resolution": {
            "count": auto_resolved_count,
            "percentage": auto_resolution_pct,
            "message": "Auto-resolution is active for common issues."
        }
    }

@app.get("/dashboard/tickets/stats")
async def get_ticket_statistics(period: Optional[str] = "week", db: Session = Depends(get_db)):
    """
    Get detailed ticket statistics for the dashboard
    
    period: 'day', 'week', 'month', or 'year'
    """
    # Calculate the date range based on the period
    now = datetime.now()
    if period == "day":
        start_date = datetime(now.year, now.month, now.day, 0, 0, 0)
    elif period == "week":
        # Start from the beginning of the week (Monday)
        days_since_monday = now.weekday()
        start_date = (now - timedelta(days=days_since_monday)).replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "month":
        start_date = datetime(now.year, now.month, 1)
    elif period == "year":
        start_date = datetime(now.year, 1, 1)
    else:
        # Default to week if invalid period
        days_since_monday = now.weekday()
        start_date = (now - timedelta(days=days_since_monday)).replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Query tickets in the date range
    tickets = db.query(Ticket).filter(Ticket.received_date >= start_date).all()
    
    # Calculate statistics
    total_count = len(tickets)
    resolved_count = sum(1 for ticket in tickets if ticket.status == "resolved")
    pending_count = sum(1 for ticket in tickets if ticket.status == "new")
    processing_count = sum(1 for ticket in tickets if ticket.status == "processing")
    
    # Calculate average resolution time
    resolution_times = []
    for ticket in tickets:
        if ticket.status == "resolved" and ticket.processed_date and ticket.received_date:
            resolution_time = (ticket.processed_date - ticket.received_date).total_seconds() / 60  # in minutes
            resolution_times.append(resolution_time)
    
    avg_resolution_time = sum(resolution_times) / len(resolution_times) if resolution_times else 0
    
    # Get ticket states for problem analysis
    ticket_states = db.query(TicketState).join(Ticket).filter(Ticket.received_date >= start_date).all()
    
    # Analyze problems
    problem_counts = {}
    for state in ticket_states:
        if state.problems:
            for problem in state.problems:
                if problem in problem_counts:
                    problem_counts[problem] += 1
                else:
                    problem_counts[problem] = 1
    
    # Sort problems by frequency
    top_problems = sorted(problem_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    
    return {
        "period": period,
        "start_date": start_date.isoformat(),
        "end_date": now.isoformat(),
        "total_tickets": total_count,
        "resolved_tickets": resolved_count,
        "pending_tickets": pending_count,
        "processing_tickets": processing_count,
        "resolution_rate": (resolved_count / total_count * 100) if total_count > 0 else 0,
        "avg_resolution_time_minutes": avg_resolution_time,
        "top_problems": [{"problem": p[0], "count": p[1]} for p in top_problems]
    }

@app.get("/dashboard/tickets/trends")
async def get_ticket_trends(period: Optional[str] = "week", db: Session = Depends(get_db)):
    """
    Get ticket trends over time for dashboard visualization
    
    period: 'day', 'week', 'month', or 'year'
    """
    # Calculate the date range based on the period
    now = datetime.now()
    if period == "day":
        start_date = datetime(now.year, now.month, now.day, 0, 0, 0)
        # For day, group by hour
        time_format = "%H:00"
        interval_hours = 1
        num_intervals = 24
    elif period == "week":
        # Start from the beginning of the week (Monday)
        days_since_monday = now.weekday()
        start_date = (now - timedelta(days=days_since_monday)).replace(hour=0, minute=0, second=0, microsecond=0)
        # For week, group by day
        time_format = "%a"  # Abbreviated weekday name
        interval_hours = 24
        num_intervals = 7
    elif period == "month":
        start_date = datetime(now.year, now.month, 1)
        # For month, group by day
        time_format = "%d"  # Day of month
        interval_hours = 24
        num_intervals = 30  # Approximate
    elif period == "year":
        start_date = datetime(now.year, 1, 1)
        # For year, group by month
        time_format = "%b"  # Abbreviated month name
        interval_hours = 24 * 30  # Approximate month in hours
        num_intervals = 12
    else:
        # Default to week if invalid period
        days_since_monday = now.weekday()
        start_date = (now - timedelta(days=days_since_monday)).replace(hour=0, minute=0, second=0, microsecond=0)
        time_format = "%a"
        interval_hours = 24
        num_intervals = 7
    
    # Query tickets in the date range
    tickets = db.query(Ticket).filter(Ticket.received_date >= start_date).all()
    
    # Initialize data structures for trends
    received_trend = {}
    resolved_trend = {}
    
    # Generate all time intervals for the period
    for i in range(num_intervals):
        interval_date = start_date + timedelta(hours=i * interval_hours)
        interval_key = interval_date.strftime(time_format)
        received_trend[interval_key] = 0
        resolved_trend[interval_key] = 0
    
    # Count tickets by time interval
    for ticket in tickets:
        # Count received tickets
        if ticket.received_date:
            received_key = ticket.received_date.strftime(time_format)
            if received_key in received_trend:
                received_trend[received_key] += 1
        
        # Count resolved tickets
        if ticket.status == "resolved" and ticket.processed_date:
            resolved_key = ticket.processed_date.strftime(time_format)
            if resolved_key in resolved_trend:
                resolved_trend[resolved_key] += 1
    
    # Convert to lists for the response
    labels = list(received_trend.keys())
    received_data = [received_trend[label] for label in labels]
    resolved_data = [resolved_trend[label] for label in labels]
    
    return {
        "period": period,
        "labels": labels,
        "received_tickets": received_data,
        "resolved_tickets": resolved_data
    }

@app.get("/dashboard/customers/stats")
async def get_customer_statistics(db: Session = Depends(get_db)):
    """
    Get customer-related statistics for the dashboard
    """
    # Get all tickets with customer information
    tickets = db.query(Ticket).all()
    
    # Count tickets by customer
    customer_ticket_counts = {}
    for ticket in tickets:
        if ticket.customer_id:
            if ticket.customer_id in customer_ticket_counts:
                customer_ticket_counts[ticket.customer_id] += 1
            else:
                customer_ticket_counts[ticket.customer_id] = 1
    
    # Find customers with most tickets
    top_customers = sorted(customer_ticket_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    
    # Get customer details for top customers
    top_customer_details = []
    for customer_id, ticket_count in top_customers:
        if customer_id in CUSTOMERS:
            customer = CUSTOMERS[customer_id]
            top_customer_details.append({
                "customer_id": customer_id,
                "name": customer.name,
                "email": customer.email,
                "ticket_count": ticket_count
            })
    
    # Calculate customer metrics
    total_customers = len(CUSTOMERS)
    customers_with_tickets = len(customer_ticket_counts)
    customers_with_resolved_tickets = 0
    customers_with_pending_tickets = 0
    
    for customer_id in customer_ticket_counts:
        has_resolved = False
        has_pending = False
        
        for ticket in tickets:
            if ticket.customer_id == customer_id:
                if ticket.status == "resolved":
                    has_resolved = True
                if ticket.status == "new":
                    has_pending = True
        
        if has_resolved:
            customers_with_resolved_tickets += 1
        if has_pending:
            customers_with_pending_tickets += 1
    
    return {
        "total_customers": total_customers,
        "customers_with_tickets": customers_with_tickets,
        "customers_with_resolved_tickets": customers_with_resolved_tickets,
        "customers_with_pending_tickets": customers_with_pending_tickets,
        "top_customers": top_customer_details
    }

@app.get("/dashboard/orders/stats")
async def get_order_statistics():
    """
    Get order-related statistics for the dashboard
    """
    # Count orders by status
    status_counts = {}
    for order in ORDERS.values():
        status = order.status.value
        if status in status_counts:
            status_counts[status] += 1
        else:
            status_counts[status] = 1
    
    # Calculate total orders and value
    total_orders = len(ORDERS)
    total_order_value = sum(order.total_amount for order in ORDERS.values())
    
    # Calculate average order value
    avg_order_value = total_order_value / total_orders if total_orders > 0 else 0
    
    # Find top selling products
    product_quantities = {}
    for order in ORDERS.values():
        for item in order.items:
            if item.product_id in product_quantities:
                product_quantities[item.product_id] += item.quantity
            else:
                product_quantities[item.product_id] = item.quantity
    
    # Get top 5 products
    top_products = sorted(product_quantities.items(), key=lambda x: x[1], reverse=True)[:5]
    
    # Get product details for top products
    top_product_details = []
    for product_id, quantity in top_products:
        if product_id in PRODUCTS:
            product = PRODUCTS[product_id]
            top_product_details.append({
                "product_id": product_id,
                "name": product.name,
                "quantity_sold": quantity,
                "revenue": quantity * product.price
            })
    
    # Calculate inventory metrics
    low_stock_count = sum(1 for inv in INVENTORY.values() if inv.quantity <= inv.reorder_threshold)
    out_of_stock_count = sum(1 for inv in INVENTORY.values() if inv.quantity == 0)
    
    return {
        "total_orders": total_orders,
        "total_order_value": total_order_value,
        "average_order_value": avg_order_value,
        "orders_by_status": status_counts,
        "top_products": top_product_details,
        "inventory_metrics": {
            "low_stock_count": low_stock_count,
            "out_of_stock_count": out_of_stock_count,
            "total_products": len(PRODUCTS)
        }
    }

if __name__ == "__main__":
    uvicorn.run("api_server:app", host="0.0.0.0", port=8000, reload=True)
