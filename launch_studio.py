"""
Launch LangGraph Studio for the Customer Support Agent
"""
import os
import subprocess
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def main():
    """
    Launch LangGraph Studio for the Customer Support Agent
    """
    print("Launching LangGraph Studio for Customer Support Agent...")
    
    # Get the current directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Change to the project directory
    os.chdir(current_dir)
    
    # Run the langgraph dev command
    try:
        subprocess.run(["langgraph", "dev"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error launching LangGraph Studio: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print("Error: 'langgraph' command not found. Make sure you have installed LangGraph correctly.")
        print("Try running: pip install langgraph")
        sys.exit(1)

if __name__ == "__main__":
    main()
