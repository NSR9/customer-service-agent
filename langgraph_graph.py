# langgraph_graph.py
from typing import List, Dict, Any, TypedDict, Optional, Union
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, BaseMessage
from agents.responder import (
    classify_and_extract,
    check_stock,
    reason_and_act,
    generate_response
)

class CustomerSupportState(TypedDict):
    # Input fields
    query: str
    context: Optional[Dict[str, Any]]
    
    # State fields
    messages: List[BaseMessage]
    problem_type: Optional[str]
    order_id: Optional[str]
    product_id: Optional[str]
    description: Optional[str]
    policy: Optional[Dict[str, str]]
    stock_available: Optional[bool]
    action_result: Optional[str]
    response: Optional[str]

def run_customer_service_graph(query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Run the customer service graph with the given query and context.
    
    Args:
        query: The customer's issue or query
        context: Optional context information
        
    Returns:
        The final state of the graph, including the response and messages
    """
    # Initialize state
    state: CustomerSupportState = {
        "query": query,
        "context": context or {},
        "messages": [HumanMessage(content=query)],
        "problem_type": None,
        "order_id": None,
        "product_id": None,
        "description": None,
        "policy": None,
        "stock_available": None,
        "action_result": None,
        "response": None
    }

    # Build the graph
    builder = StateGraph(CustomerSupportState)
    
    # Add nodes
    builder.add_node("classify_and_extract", classify_and_extract)
    builder.add_node("check_stock", check_stock)
    builder.add_node("reason_and_act", reason_and_act)
    builder.add_node("generate_response", generate_response)
    
    # Set the entry point
    builder.set_entry_point("classify_and_extract")
    
    # Define conditional edges
    def route_after_classification(state: CustomerSupportState) -> str:
        """Route to the next node after classification."""
        # Always check stock after classification
        return "check_stock"
    
    def route_after_stock_check(state: CustomerSupportState) -> str:
        """Route to the next node after stock check."""
        # Always proceed to reason and act
        return "reason_and_act"
    
    # Add edges
    builder.add_conditional_edges(
        "classify_and_extract",
        route_after_classification
    )
    
    builder.add_conditional_edges(
        "check_stock",
        route_after_stock_check
    )
    
    builder.add_edge("reason_and_act", "generate_response")
    builder.add_edge("generate_response", END)
    
    # Compile the graph
    graph = builder.compile()
    
    # Execute the graph
    result = graph.invoke(state)
    
    return result