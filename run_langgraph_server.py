"""
Run the customer support agent on the LangGraph dev server
"""
import os
import json
from dotenv import load_dotenv
from langgraph.dev import dev_server
from graph import graph_app

# Load environment variables from .env file
load_dotenv()

def load_test_scenarios():
    """Load test scenarios from the JSON file"""
    try:
        with open('test_scenarios.json', 'r') as f:
            scenarios = json.load(f)
        
        # Extract examples and labels
        examples = [scenario['input'] for scenario in scenarios]
        labels = [scenario['name'] for scenario in scenarios]
        
        return examples, labels
    except Exception as e:
        print(f"Error loading test scenarios: {e}")
        # Fallback examples
        return [
            {"messages": [{"type": "human", "content": "I never received my order #ORD12345"}]},
            {"messages": [{"type": "human", "content": "My package arrived damaged"}]},
            {"messages": [{"type": "human", "content": "I received the wrong item in my order"}]}
        ], ["Non-delivery Issue", "Damaged Item", "Wrong Item"]

def main():
    # Load test scenarios
    examples, example_labels = load_test_scenarios()
    
    # Start the LangGraph dev server
    dev_server(
        graph_app,
        examples=examples,
        example_labels=example_labels
    )

if __name__ == "__main__":
    main()
