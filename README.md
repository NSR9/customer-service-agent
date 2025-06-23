# Customer Support Agent with LangGraph

This project implements an intelligent customer support agent using LangGraph that can handle customer issue tickets, classify problems, find relevant policies, and take appropriate actions based on the issue and available inventory. It includes a FastAPI server for processing tickets via REST API and stores all ticket data in PostgreSQL.

## Features

- **Structured Output with Pydantic Models**: Uses IssueClassification and PolicySelection models for robust type safety
- **LangGraph Integration**: Multi-step workflow with issue classification, policy selection, and resolution
- **Detailed Reasoning Capture**: Transparent agent reasoning with emoji-prefixed messages
- **ERP System Integration**: Simulated backend with products, inventory, orders, and shipments
- **Tool-based Problem Solving**: Support for order status checking, tracking, stock checking, resending items, and processing refunds
- **FastAPI Server**: Asynchronous ticket processing with background tasks
- **PostgreSQL Database**: Persistent storage for tickets and detailed agent reasoning

## System Architecture

### Core Components

1. **State Management (state.py)**
   - SupportAgentState Pydantic model tracks messages, problems, policies, actions, and reasoning
   - Maintains conversation history with structured message types

2. **LangGraph Workflow (graph.py)**
   - Three-node workflow: classify_issue → pick_policy → resolve_issue
   - Each node updates the state with additional reasoning and actions

3. **ERP Simulator**
   - Database models for Products, Inventory, Orders, Shipments, Customers, etc.
   - Service layer for querying and updating ERP data

4. **API Server (api_server.py)**
   - FastAPI endpoints for ticket creation and status checking
   - Background task processing for asynchronous ticket handling

5. **Database Integration (database/ticket_db.py)**
   - PostgreSQL models for tickets and their processing state
   - Functions to save and retrieve ticket data with detailed reasoning

## Project Structure

```
├── agents/                # Agent components
├── database/              # Database and ERP simulation
│   ├── data.py            # Sample ERP data
│   ├── models.py          # ERP system data models
│   ├── service.py         # ERP system service layer
│   └── ticket_db.py       # PostgreSQL database models for tickets
├── api_server.py          # FastAPI server for ticket processing
├── create_db.py           # Database creation script
├── docker-compose.yml     # Docker Compose for PostgreSQL
├── graph.py               # LangGraph workflow definition
├── init_db.py             # Database initialization script
├── nodes.py               # LangGraph node implementations
├── policies.py            # Support policies definitions
├── pyproject.toml         # Project configuration for uv
├── requirements.txt       # Project dependencies
├── state.py               # State management for LangGraph
├── test_scenarios.json    # Test cases for the agent
├── tools.py               # Tool implementations for the agent
└── uv.lock                # Lock file for uv package manager
```

## Setup with uv Package Manager

### 1. Install uv

If you don't have uv installed, install it first:

```bash
# Using pip
pip install uv

# Using Homebrew (macOS)
brew install uv
```

### 2. Clone the Repository

```bash
git clone https://github.com/NSR9/customer-service-agent.git
cd customer-service-agent
```

### 3. Create and Activate Virtual Environment with uv

```bash
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 4. Install Dependencies with uv

```bash
uv pip install -r requirements.txt
```

Alternatively, if you have a pyproject.toml file:

```bash
uv pip install -e .
```

### 5. Environment Configuration

Create a `.env` file based on the provided templates:

```bash
cp .env.template .env
```

Edit the `.env` file to add your OpenAI API key and adjust database settings:

```
# OpenAI API Key (required)
OPENAI_API_KEY=your-api-key-here

# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=postgres
DB_NAME=support_tickets
```

### 6. Start PostgreSQL Database

Using Docker Compose:

```bash
docker-compose up -d
```

This will start a PostgreSQL instance with the configuration specified in your docker-compose.yml file.

### 7. Initialize the Database

```bash
python init_db.py
```

This script creates the necessary tables and populates them with sample data for testing.

## Running the System

### Option 1: FastAPI Server

Start the FastAPI server to process tickets via REST API:

```bash
uvicorn api_server:app --reload --host 0.0.0.0 --port 8000
```

The server will be available at http://localhost:8000 with API documentation at http://localhost:8000/docs.

#### API Usage Examples

```bash
# Create a new ticket
curl -X POST "http://localhost:8000/tickets/" \
  -H "Content-Type: application/json" \
  -d '{"ticket_id":"TICKET-001","customer_id":"CUST-001","ticket_description":"I ordered headphones in my order #ORD54321, but received a water bottle instead. What should I do?","received_date":"2025-06-22T23:00:00Z"}'

# Get ticket details
curl "http://localhost:8000/tickets/TICKET-001"
```

### Option 2: LangGraph Studio

Visualize and debug the agent workflow using LangGraph Studio:

```bash
python run_langgraph_server.py
```

Then navigate to the URL provided in the console output (typically http://localhost:3000).

## Testing

The project includes test scenarios in `test_scenarios.json` that you can use to test the agent:

```bash
python test_api.py
```

This will run through predefined customer issues and verify the agent's responses.

## Understanding the Agent Workflow

### 1. Issue Classification

The agent first classifies the customer issue into problem types like:
- non-delivery, delayed, damaged, wrong-item, quality, fit, return, refund, etc.

It uses structured output with Pydantic models to ensure type safety.

### 2. Policy Selection

Based on the identified problem types, the agent selects the most appropriate company policy to apply. The reasoning process is captured with emoji prefixes for better readability:

- 🔍 **Policy Analysis**: Detailed reasoning for policy selection
- 📋 **Selected Policy**: The chosen policy and its description

### 3. Issue Resolution

The agent uses tools to gather information and resolve the issue:

- 🤔 **Tool Thoughts**: Agent's reasoning before using a tool
- 🔧 **Tool Calls**: The specific tool being used and its input
- 📊 **Tool Responses**: Results returned from the tool
- ✅ **Final Resolution**: The action taken and explanation to the customer

## Available Tools

1. **check_order_status**: Get order details by ID (e.g., ORD12345)
2. **track_order**: Get tracking information for orders
3. **check_stock**: Check product availability (Products: P1001-P1005)
4. **initialize_resend**: Process replacement shipments
5. **initialize_refund**: Process returns and refunds

## Product and Order Reference

- **Product IDs**: P1001 (Headphones), P1002 (Watch), P1003 (T-Shirt), P1004 (Water Bottle), P1005 (Charging Pad)
- **Order IDs**: ORD12345, ORD67890, ORD54321, ORD13579

## Extending the System

### Adding New Tools

1. Define the tool function in `tools.py`
2. Add it to the tools list in `nodes.py`
3. Update the ERP service in `database/service.py` if needed

### Adding New Policies

Update the policies dictionary in `policies.py` with new policy definitions.

### Modifying the Workflow

Edit the graph structure in `graph.py` to add or modify workflow steps.

## Troubleshooting

### Database Connection Issues

If you encounter database connection problems:

```bash
# Check if PostgreSQL container is running
docker ps

# View PostgreSQL logs
docker logs <container_id>

# Restart the container if needed
docker-compose restart
```

### API Key Issues

Ensure your OpenAI API key is correctly set in the `.env` file and has sufficient permissions and credits.

### Package Dependency Issues

If you encounter dependency conflicts, try:

```bash
uv pip install --upgrade -r requirements.txt
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.