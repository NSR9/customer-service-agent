# Customer Support Agent with LangGraph

This project implements a customer support agent using LangGraph that can handle customer issue tickets, classify problems, find relevant policies, and take appropriate actions based on the issue and available inventory. It includes a FastAPI server for processing tickets via REST API and stores all ticket data in PostgreSQL.

## Features

- Issue classification and information extraction
- Policy matching based on issue type
- Inventory checking
- Action determination using ReAct agent pattern
- Support for multiple tools: order status checking, order tracking, stock checking, resending items, and processing refunds
- FastAPI server for ticket processing via REST API
- PostgreSQL database integration for ticket and state storage

## Project Structure

```
├── agents/
│   ├── __init__.py
│   └── responder.py       # Contains the agent functionality and tools
├── database/
│   ├── __init__.py
│   ├── data.py            # Sample data for the ERP system
│   ├── models.py          # ERP system data models
│   ├── service.py         # ERP system service layer
│   └── ticket_db.py       # PostgreSQL database models for tickets
├── api_server.py          # FastAPI server for ticket processing
├── docker-compose.yml     # Docker Compose for PostgreSQL
├── graph.py              # LangGraph workflow definition
├── init_db.py            # Database initialization script
├── langgraph_graph.py    # Defines the LangGraph state and flow
├── main.py               # Demo script to run the customer support agent
├── nodes.py              # LangGraph node implementations
├── policies.py           # Support policies definitions
├── requirements.txt      # Project dependencies
├── state.py              # State management for LangGraph
├── tools.py              # Tool implementations for the agent
└── README.md             # This file
```

## Setup

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file based on the `.env.template`:
   ```bash
   cp .env.template .env
   ```
   Then edit the `.env` file to add your OpenAI API key and adjust the database settings if needed.

4. Start the PostgreSQL database using Docker Compose:
   ```bash
   docker-compose up -d
   ```

5. Initialize the database tables:
   ```bash
   python init_db.py
   ```

## Running the Demo

### Option 1: Command Line Demo

```bash
python main.py
```

The demo will present example customer issues or allow you to enter your own issue. The agent will then:

1. Classify the issue and extract relevant information
2. Check inventory if needed
3. Determine the appropriate action using the ReAct agent
4. Generate a final response

### Option 2: FastAPI Server

Run the FastAPI server to process tickets via REST API:

```bash
uvicorn api_server:app --reload
```

The server will be available at http://localhost:8000. You can access the API documentation at http://localhost:8000/docs.

Example API usage:

```bash
# Create a new ticket
curl -X POST "http://localhost:8000/tickets/" \
  -H "Content-Type: application/json" \
  -d '{"ticket_id":"TICKET-001","customer_id":"CUST-001","ticket_description":"I ordered product2 in my order #ORD54321, but received product4 instead. What should I do?","received_date":"2025-06-22T23:00:00Z"}'

# Get ticket details
curl "http://localhost:8000/tickets/TICKET-001"

# List all tickets
curl "http://localhost:8000/tickets/"
```

The ticket processing happens asynchronously in the background, and the results are stored in the PostgreSQL database.

### Option 3: LangGraph Studio

You can also run the agent in LangGraph Studio, which provides a visual interface for testing and debugging:

```bash
langgraph dev
```

This will start the LangGraph Studio server, which you can access in your browser. The studio provides:

- Visual graph representation
- Step-by-step execution visualization
- State inspection at each node
- Test scenarios from the examples

## State Management

The agent maintains the following state throughout the process:

- `query`: The original customer issue
- `context`: Additional context information
- `messages`: List of messages (Human, AI, Tool)
- `problem_type`: Classified issue type
- `order_id`: Extracted order ID
- `product_id`: Extracted product ID
- `description`: Issue description
- `policy`: Matched policy information
- `stock_available`: Whether the item is in stock
- `action_result`: Result of the action taken
- `response`: Final response to the customer

## Extending the Agent

To extend the agent with additional functionality:

1. Add new tools in `agents/responder.py`
2. Update the policies in `POLICIES` dictionary
3. Modify the graph flow in `langgraph_graph.py` if needed