"""
Migration script to add the messages column to the ticket_states table
"""
import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def add_messages_column():
    """
    Add the messages column to the ticket_states table
    """
    # Get database connection string from environment variables
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://vee:password@localhost:5432/support_tickets")
    
    # Extract connection parameters from DATABASE_URL
    if "://" in DATABASE_URL:
        auth_part = DATABASE_URL.split("://")[1].split("@")[0]
        user_pass = auth_part.split(":")
        user = user_pass[0]
        password = user_pass[1] if len(user_pass) > 1 else ""
        
        host_part = DATABASE_URL.split("@")[1].split("/")[0]
        host_port = host_part.split(":")
        host = host_port[0]
        port = host_port[1] if len(host_port) > 1 else "5432"
        
        database = DATABASE_URL.split("/")[-1].split("?")[0]
        
        # Connect to the database
        conn_params = {
            "host": host,
            "port": port,
            "user": user,
            "password": password,
            "database": database
        }
        
        try:
            # Connect to the database
            print(f"Connecting to database: {database} at {host}:{port} as {user}")
            conn = psycopg2.connect(**conn_params)
            conn.autocommit = False
            cursor = conn.cursor()
            
            # Check if the messages column already exists
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'ticket_states' AND column_name = 'messages'
            """)
            
            if cursor.fetchone():
                print("The 'messages' column already exists in the ticket_states table.")
                return
            
            # Add the messages column
            print("Adding 'messages' column to the ticket_states table...")
            cursor.execute("ALTER TABLE ticket_states ADD COLUMN messages JSONB;")
            
            # Commit the changes
            conn.commit()
            print("Successfully added 'messages' column to the ticket_states table.")
            
        except Exception as e:
            conn.rollback()
            print(f"Error adding 'messages' column: {str(e)}")
            raise e
        finally:
            cursor.close()
            conn.close()
    else:
        print(f"Invalid DATABASE_URL format: {DATABASE_URL}")
        return False

if __name__ == "__main__":
    add_messages_column() 