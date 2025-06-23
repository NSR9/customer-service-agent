"""
Customer Support Agent Responder Module
This module contains the functions for the customer support agent to handle customer issues.
"""
from typing import Dict, List, Any, Optional, TypedDict, Union, Literal
import json
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langchain_core.tools import tool
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_openai import ChatOpenAI

# Define policies
POLICIES = {
    "damaged_product": {
        "name": "Damaged Product Policy",
        "description": "If a customer receives a damaged product, we will replace it free of charge if in stock, or issue a full refund."
    },
    "missing_item": {
        "name": "Missing Item Policy",
        "description": "If an item is missing from an order, we will send the missing item if in stock, or issue a refund for that item."
    },
    "wrong_item": {
        "name": "Wrong Item Policy",
        "description": "If a customer receives the wrong item, we will send the correct item if in stock and provide a return label for the wrong item, or issue a full refund."
    },
    "late_delivery": {
        "name": "Late Delivery Policy",
        "description": "If a delivery is more than 7 days late, the customer is eligible for a partial refund or store credit."
    },
    "defective_product": {
        "name": "Defective Product Policy",
        "description": "If a product is defective, we will replace it with a new one if in stock, or issue a full refund."
    }
}

# Define the inventory database (mock)
INVENTORY = {
    "product1": 10,
    "product2": 0,
    "product3": 5,
    "product4": 3,
    "product5": 0
}

# Define the orders database (mock)
ORDERS = {
    "ORD12345": {
        "customer": "John Doe",
        "items": ["product1", "product3"],
        "status": "delivered",
        "address": "123 Main St, Anytown, USA"
    },
    "ORD67890": {
        "customer": "Jane Smith",
        "items": ["product2", "product4"],
        "status": "shipped",
        "address": "456 Oak Ave, Somewhere, USA"
    },
    "ORD54321": {
        "customer": "Bob Johnson",
        "items": ["product5"],
        "status": "processing",
        "address": "789 Pine Rd, Nowhere, USA"
    }
}

# Define the tracking database (mock)
TRACKING = {
    "ORD12345": [
        {"timestamp": "2023-06-15T10:00:00", "status": "Order Received", "location": "Warehouse"},
        {"timestamp": "2023-06-16T14:30:00", "status": "Shipped", "location": "Distribution Center"},
        {"timestamp": "2023-06-18T09:15:00", "status": "Delivered", "location": "Customer Address"}
    ],
    "ORD67890": [
        {"timestamp": "2023-06-17T11:20:00", "status": "Order Received", "location": "Warehouse"},
        {"timestamp": "2023-06-18T16:45:00", "status": "Shipped", "location": "Distribution Center"}
    ],
    "ORD54321": [
        {"timestamp": "2023-06-19T13:10:00", "status": "Order Received", "location": "Warehouse"}
    ]
}

# Tool definitions
class OrderStatusInput(BaseModel):
    order_id: str = Field(description="The order ID to check status for")

@tool("check_order_status", args_schema=OrderStatusInput)
def check_order_status(order_id: str) -> str:
    """Check the status of a customer order."""
    if order_id in ORDERS:
        return json.dumps({"order_id": order_id, "status": ORDERS[order_id]["status"]})
    return json.dumps({"error": "Order not found"})

class TrackOrderInput(BaseModel):
    order_id: str = Field(description="The order ID to track")

@tool("track_order", args_schema=TrackOrderInput)
def track_order(order_id: str) -> str:
    """Get the tracking history of an order."""
    if order_id in TRACKING:
        return json.dumps({"order_id": order_id, "tracking_history": TRACKING[order_id]})
    return json.dumps({"error": "Tracking information not found"})

class CheckStockInput(BaseModel):
    product_id: str = Field(description="The product ID to check stock for")

@tool("check_stock", args_schema=CheckStockInput)
def check_stock_tool(product_id: str) -> str:
    """Check if a product is in stock."""
    if product_id in INVENTORY:
        return json.dumps({"product_id": product_id, "stock": INVENTORY[product_id]})
    return json.dumps({"error": "Product not found"})

class InitializeResendInput(BaseModel):
    order_id: str = Field(description="The order ID to resend")
    product_id: str = Field(description="The product ID to resend")

@tool("initialize_resend", args_schema=InitializeResendInput)
def initialize_resend(order_id: str, product_id: str) -> str:
    """Initialize a product resend to the customer."""
    if order_id not in ORDERS:
        return json.dumps({"error": "Order not found"})
    if product_id not in INVENTORY:
        return json.dumps({"error": "Product not found"})
    if INVENTORY[product_id] <= 0:
        return json.dumps({"error": "Product out of stock"})
    
    # In a real system, this would initiate the resend process
    return json.dumps({
        "success": True,
        "message": f"Resend of {product_id} for order {order_id} has been initiated",
        "shipping_address": ORDERS[order_id]["address"]
    })

class InitializeRefundInput(BaseModel):
    order_id: str = Field(description="The order ID to refund")
    product_id: str = Field(description="The product ID to refund")
    reason: str = Field(description="The reason for the refund")

@tool("initialize_refund", args_schema=InitializeRefundInput)
def initialize_refund(order_id: str, product_id: str, reason: str) -> str:
    """Initialize a refund for the customer."""
    if order_id not in ORDERS:
        return json.dumps({"error": "Order not found"})
    if product_id not in INVENTORY:
        return json.dumps({"error": "Product not found"})
    
    # In a real system, this would initiate the refund process
    return json.dumps({
        "success": True,
        "message": f"Refund for {product_id} from order {order_id} has been initiated",
        "reason": reason
    })

# Define the functions for the customer support agent
def classify_and_extract(state):
    """Classify the customer issue and extract relevant information."""
    llm = ChatOpenAI(model="gpt-4o")
    
    # Classify the issue
    classification_prompt = f"""
    You are a customer service agent. Analyze the following customer issue:
    
    {state['query']}
    
    Classify this issue into one of the following categories:
    - damaged_product
    - missing_item
    - wrong_item
    - late_delivery
    - defective_product
    
    Also extract the following information:
    - Order ID (if mentioned)
    - Product ID (if mentioned)
    - Description of the issue
    
    Return your response as a JSON object with the following structure:
    {{
        "issue_type": "category_name",
        "order_id": "order_id_if_found_or_null",
        "product_id": "product_id_if_found_or_null",
        "description": "brief_description_of_issue"
    }}
    """
    
    classification_response = llm.invoke(classification_prompt)
    classification_data = json.loads(classification_response.content)
    
    # Update the state with classification data
    state["problem_type"] = classification_data["issue_type"]
    state["order_id"] = classification_data.get("order_id")
    state["product_id"] = classification_data.get("product_id")
    state["description"] = classification_data.get("description")
    
    # Add the policy to the state
    if state["problem_type"] in POLICIES:
        state["policy"] = POLICIES[state["problem_type"]]
    else:
        state["policy"] = {
            "name": "General Customer Service Policy",
            "description": "We aim to resolve all customer issues promptly and to their satisfaction."
        }
    
    # Add AI message to the state
    ai_response = f"I understand that you have an issue with {state['problem_type']}. "
    if state["order_id"]:
        ai_response += f"For order {state['order_id']}. "
    if state["product_id"]:
        ai_response += f"Regarding product {state['product_id']}. "
    ai_response += f"According to our {state['policy']['name']}, {state['policy']['description']}"
    
    state["messages"].append(AIMessage(content=ai_response))
    
    return state

def check_stock(state):
    """Check if the product is in stock."""
    if not state["product_id"]:
        state["stock_available"] = False
        state["messages"].append(ToolMessage(
            content="Unable to check stock without a product ID.",
            tool_call_id="check_stock"
        ))
        return state
    
    # Use the check_stock_tool to check if the product is in stock
    stock_result = json.loads(check_stock_tool(state["product_id"]))
    
    if "error" in stock_result:
        state["stock_available"] = False
        state["messages"].append(ToolMessage(
            content=f"Error checking stock: {stock_result['error']}",
            tool_call_id="check_stock"
        ))
    else:
        state["stock_available"] = stock_result["stock"] > 0
        state["messages"].append(ToolMessage(
            content=f"Product {state['product_id']} has {stock_result['stock']} units in stock.",
            tool_call_id="check_stock"
        ))
    
    return state

def reason_and_act(state):
    """Reason about the issue and take appropriate action."""
    llm = ChatOpenAI(model="gpt-4o")
    
    # Create a list of available tools
    tools = [
        check_order_status,
        track_order,
        check_stock_tool,
        initialize_resend,
        initialize_refund
    ]
    
    # Create a prompt for the ReAct agent
    react_prompt = f"""
    You are a customer service agent helping a customer with an issue.
    
    Customer Issue: {state['query']}
    Issue Type: {state['problem_type']}
    Order ID: {state['order_id'] if state['order_id'] else 'Unknown'}
    Product ID: {state['product_id'] if state['product_id'] else 'Unknown'}
    Description: {state['description']}
    Policy: {state['policy']['name']} - {state['policy']['description']}
    Stock Available: {state['stock_available'] if state['stock_available'] is not None else 'Unknown'}
    
    Based on the above information, determine what action to take.
    If the stock is available (stock_available is True) and the issue requires a replacement, use initialize_resend.
    If the stock is not available (stock_available is False) or the issue requires a refund, use initialize_refund.
    You may need to check the order status or track the order first to gather more information.
    
    Think step by step about what tools you need to use and in what order.
    """
    
    # Use the ReAct agent to determine the action
    from langchain.agents import create_react_agent
    from langchain.agents.agent import AgentExecutor
    
    agent = create_react_agent(llm, tools, react_prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
    
    # Execute the agent
    try:
        agent_result = agent_executor.invoke({"input": state['query']})
        action_result = agent_result["output"]
        
        # Add the result to the state
        state["action_result"] = action_result
        state["messages"].append(AIMessage(content=action_result))
    except Exception as e:
        state["action_result"] = f"Error executing action: {str(e)}"
        state["messages"].append(AIMessage(content=f"I apologize, but I encountered an error while trying to resolve your issue: {str(e)}"))
    
    return state

def generate_response(state):
    """Generate the final response to the customer."""
    llm = ChatOpenAI(model="gpt-4o")
    
    # Create a summary of what happened
    summary_prompt = f"""
    You are a customer service agent. Summarize the interaction with the customer and the actions taken.
    
    Customer Issue: {state['query']}
    Issue Type: {state['problem_type']}
    Policy Applied: {state['policy']['name']}
    Action Result: {state['action_result'] if state['action_result'] else 'No action taken'}
    
    Provide a concise, professional, and empathetic response to the customer that:
    1. Acknowledges their issue
    2. Explains what action was taken
    3. Provides next steps or what they can expect
    4. Thanks them for their patience
    """
    
    final_response = llm.invoke(summary_prompt)
    state["response"] = final_response.content
    
    # Add the final response to the messages
    state["messages"].append(AIMessage(content=state["response"]))
    
    return state
