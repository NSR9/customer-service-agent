"""
FastAPI server for Customer Support Agent
"""
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict, Any, List
import uvicorn
import uuid
from sqlalchemy.orm import Session

# Import graph components
from graph import graph_app
from state import SupportAgentState
from langchain_core.messages import HumanMessage

# Import database components
from database.ticket_db import get_db, save_ticket_state, Ticket, TicketState

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

class TicketResponse(BaseModel):
    ticket_id: str
    status: str
    message: str
    problems: Optional[List[str]] = None
    policy_name: Optional[str] = None
    action_taken: Optional[str] = None

class TicketDetailResponse(TicketResponse):
    customer_id: str
    description: str
    received_date: datetime
    processed_date: Optional[datetime] = None
    policy_desc: Optional[str] = None
    reason: Optional[str] = None
    reasoning: Optional[Dict[str, Any]] = None
    thought_process: Optional[List[Dict[str, Any]]] = None

# Process ticket in background
def process_ticket_task(ticket_data: Dict[str, Any]):
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
        
        # Handle different state object types
        # If final_state is a dict-like object (AddableValuesDict)
        if hasattr(final_state, 'get'):
            # Extract relevant fields safely using get() method
            problems = final_state.get('problems', [])
            actions = final_state.get('actions', None)
            action_taken = actions[0] if isinstance(actions, list) and actions else None
            print(f"Problems identified: {problems}")
            print(f"Action taken: {action_taken}")
        else:
            # Try to access attributes directly if it's an object with attributes
            problems = getattr(final_state, 'problems', []) if hasattr(final_state, 'problems') else []
            action_taken = getattr(final_state, 'action_taken', None) if hasattr(final_state, 'action_taken') else None
            print(f"Problems identified: {problems}")
            print(f"Action taken: {action_taken}")
        
        # Save ticket and state to database
        save_ticket_state(ticket_data, final_state)
        
        return final_state
    except Exception as e:
        print(f"Error processing ticket {ticket_data['ticket_id']}: {str(e)}")
        # Re-raise the exception to be handled by the caller
        raise e

@app.post("/tickets/", response_model=TicketResponse)
async def create_ticket(
    ticket: TicketRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Create a new support ticket and process it asynchronously
    """
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
        
        # Prepare ticket data for background processing
        ticket_data = {
            "ticket_id": ticket.ticket_id,
            "customer_id": ticket.customer_id,
            "description": ticket.ticket_description,
            "received_date": ticket.received_date,
            "status": "processing"
        }
        
        # Add ticket processing to background tasks
        background_tasks.add_task(process_ticket_task, ticket_data)
        
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
    
    # Get the ticket state
    ticket_state = db.query(TicketState).filter(TicketState.ticket_id == ticket.id).first()
    
    if not ticket_state:
        return {
            "ticket_id": ticket.ticket_id,
            "status": ticket.status,
            "message": "Ticket found but processing not complete",
            "customer_id": ticket.customer_id,
            "description": ticket.description,
            "received_date": ticket.received_date,
            "processed_date": ticket.processed_date
        }
    
    # Return full ticket details with state
    return {
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
        "thought_process": ticket_state.thought_process
    }

@app.get("/tickets/", response_model=List[TicketResponse])
async def list_tickets(db: Session = Depends(get_db)):
    """
    List all tickets
    """
    tickets = db.query(Ticket).all()
    
    result = []
    for ticket in tickets:
        ticket_state = db.query(TicketState).filter(TicketState.ticket_id == ticket.id).first()
        
        ticket_data = {
            "ticket_id": ticket.ticket_id,
            "status": ticket.status,
            "message": "Ticket found",
            "customer_id": ticket.customer_id
        }
        
        if ticket_state:
            ticket_data.update({
                "problems": ticket_state.problems,
                "policy_name": ticket_state.policy_name,
                "action_taken": ticket_state.action_taken
            })
        
        result.append(ticket_data)
    
    return result

if __name__ == "__main__":
    uvicorn.run("api_server:app", host="0.0.0.0", port=8000, reload=True)
