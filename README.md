# Customer Support Agent with LangGraph

This project implements a customer support agent using LangGraph that can handle customer issue tickets, classify problems, find relevant policies, and take appropriate actions based on the issue and available inventory.

## Features

- Issue classification and information extraction
- Policy matching based on issue type
- Inventory checking
- Action determination using ReAct agent pattern
- Support for multiple tools: order status checking, order tracking, stock checking, resending items, and processing refunds

## Project Structure

```
├── agents/
│   ├── __init__.py
│   └── responder.py    # Contains the agent functionality and tools
├── langgraph_graph.py  # Defines the LangGraph state and flow
├── main.py             # Demo script to run the customer support agent
├── requirements.txt    # Project dependencies
└── README.md           # This file
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

3. Create a `.env` file with your OpenAI API key:
   ```
   OPENAI_API_KEY=your_api_key_here
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

### Option 2: LangGraph Studio

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