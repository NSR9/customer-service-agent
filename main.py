"""
Customer Support Agent Demo
This script demonstrates the customer support agent built with LangGraph.
"""
import os
from dotenv import load_dotenv
from langgraph_graph import run_customer_service_graph

# Load environment variables from .env file (for API keys)
load_dotenv()

def main():
    print("Customer Support Agent Demo")
    print("===========================")
    
    # Example customer issues
    examples = [
        "I received my order #ORD12345 yesterday, but the product1 is damaged. The packaging was fine but the item inside is cracked.",
        "My order #ORD67890 was supposed to arrive last week, but I still haven't received it. Can you help me track it?",
        "I ordered product2 in my order #ORD54321, but received product4 instead. What should I do?",
        "The product3 I received in order #ORD12345 is defective. It doesn't work at all when I try to use it."
    ]
    
    # Let user select an example or enter their own issue
    print("\nSelect an example issue or enter your own:")
    for i, example in enumerate(examples):
        print(f"{i+1}. {example}")
    print("0. Enter your own issue")
    
    choice = input("\nEnter your choice (0-4): ")
    
    if choice == "0":
        customer_issue = input("\nEnter your issue: ")
    else:
        try:
            index = int(choice) - 1
            if 0 <= index < len(examples):
                customer_issue = examples[index]
            else:
                customer_issue = input("\nInvalid choice. Enter your issue: ")
        except ValueError:
            customer_issue = input("\nInvalid choice. Enter your issue: ")
    
    print("\nProcessing your issue...")
    print("------------------------")
    
    # Run the customer support agent
    result = run_customer_service_graph(customer_issue)
    
    # Display the conversation
    print("\nConversation:")
    print("-------------")
    for message in result["messages"]:
        if message.type == "human":
            print(f"\nCustomer: {message.content}")
        elif message.type == "ai":
            print(f"\nAgent: {message.content}")
        elif message.type == "tool":
            print(f"\nSystem: {message.content}")
    
    print("\n------------------------")
    print("Customer support process completed.")

if __name__ == "__main__":
    main()
