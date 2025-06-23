"""
PostgreSQL database integration for storing support ticket data
"""
from sqlalchemy import create_engine, Column, String, Integer, DateTime, JSON, Text, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

# Get database connection string from environment variables
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/support_tickets")

# Create SQLAlchemy engine and session
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Ticket(Base):
    """
    Database model for support tickets
    """
    __tablename__ = "tickets"
    
    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(String, unique=True, index=True)
    customer_id = Column(String, index=True)
    description = Column(Text)
    received_date = Column(DateTime, default=datetime.now)
    processed_date = Column(DateTime, nullable=True)
    status = Column(String, default="new")  # new, processing, resolved
    
    # Relationships
    state_data = relationship("TicketState", back_populates="ticket", uselist=False, cascade="all, delete-orphan")
    
    def to_dict(self):
        return {
            "id": self.id,
            "ticket_id": self.ticket_id,
            "customer_id": self.customer_id,
            "description": self.description,
            "received_date": self.received_date.isoformat() if self.received_date else None,
            "processed_date": self.processed_date.isoformat() if self.processed_date else None,
            "status": self.status
        }

class TicketState(Base):
    """
    Database model for storing the complete state of a ticket after processing
    """
    __tablename__ = "ticket_states"
    
    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"))
    
    # State data from SupportAgentState
    problems = Column(JSON)  # List of problem types
    policy_name = Column(String, nullable=True)
    policy_desc = Column(Text, nullable=True)
    policy_reason = Column(Text, nullable=True)
    action_taken = Column(String, nullable=True)
    reason = Column(Text, nullable=True)
    reasoning = Column(JSON, nullable=True)  # Dict of reasoning steps
    thought_process = Column(JSON, nullable=True)  # List of thought process steps
    
    # Relationship
    ticket = relationship("Ticket", back_populates="state_data")
    
    def to_dict(self):
        return {
            "id": self.id,
            "ticket_id": self.ticket_id,
            "problems": self.problems,
            "policy_name": self.policy_name,
            "policy_desc": self.policy_desc,
            "policy_reason": self.policy_reason,
            "action_taken": self.action_taken,
            "reason": self.reason,
            "reasoning": self.reasoning,
            "thought_process": self.thought_process
        }

# Create all tables
def create_tables():
    Base.metadata.create_all(bind=engine)

# Get a database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Save ticket and state to database
def save_ticket_state(ticket_data, state_data):
    """
    Save ticket and its state to the database
    
    Args:
        ticket_data: Dictionary with ticket information
        state_data: State object (could be SupportAgentState or AddableValuesDict)
    
    Returns:
        Ticket object
    """
    db = SessionLocal()
    try:
        # Check if ticket already exists
        existing_ticket = db.query(Ticket).filter(Ticket.ticket_id == ticket_data["ticket_id"]).first()
        
        if existing_ticket:
            # Update existing ticket
            ticket = existing_ticket
            ticket.processed_date = datetime.now()
            ticket.status = "resolved"
        else:
            # Create new ticket
            ticket = Ticket(
                ticket_id=ticket_data["ticket_id"],
                customer_id=ticket_data["customer_id"],
                description=ticket_data["description"],
                received_date=datetime.fromisoformat(ticket_data["received_date"]) if isinstance(ticket_data["received_date"], str) else ticket_data["received_date"],
                processed_date=datetime.now(),
                status="resolved"
            )
            db.add(ticket)
            
        db.flush()  # Flush to get the ticket ID
        
        # Check if state already exists for this ticket
        existing_state = db.query(TicketState).filter(TicketState.ticket_id == ticket.id).first()
        
        # Extract state data based on the object type
        # Handle AddableValuesDict (dict-like object)
        if hasattr(state_data, 'get'):
            problems = state_data.get('problems', [])
            actions = state_data.get('actions', [])
            action_taken = actions[0] if isinstance(actions, list) and actions else None
            policy = state_data.get('policy', {})
            policy_name = policy.get('name') if isinstance(policy, dict) else None
            policy_desc = policy.get('description') if isinstance(policy, dict) else None
            policy_reason = policy.get('reason') if isinstance(policy, dict) else None
            reasoning = state_data.get('reasoning', {})
            thought_process = state_data.get('thought_process', [])
            messages = state_data.get('messages', [])
            reason = None
            
            # Try to extract reason from messages
            if messages and isinstance(messages, list):
                for msg in reversed(messages):  # Look from the end
                    if hasattr(msg, 'content') and msg.content and '✅' in msg.content:
                        reason = msg.content
                        break
        else:
            # Handle SupportAgentState object with attributes
            problems = getattr(state_data, 'problems', []) if hasattr(state_data, 'problems') else []
            policy_name = getattr(state_data, 'policy_name', None) if hasattr(state_data, 'policy_name') else None
            policy_desc = getattr(state_data, 'policy_desc', None) if hasattr(state_data, 'policy_desc') else None
            policy_reason = getattr(state_data, 'policy_reason', None) if hasattr(state_data, 'policy_reason') else None
            action_taken = getattr(state_data, 'action_taken', None) if hasattr(state_data, 'action_taken') else None
            reason = getattr(state_data, 'reason', None) if hasattr(state_data, 'reason') else None
            reasoning = getattr(state_data, 'reasoning', {}) if hasattr(state_data, 'reasoning') else {}
            thought_process = getattr(state_data, 'thought_process', []) if hasattr(state_data, 'thought_process') else []
        
        if existing_state:
            # Update existing state
            existing_state.problems = problems
            existing_state.policy_name = policy_name
            existing_state.policy_desc = policy_desc
            existing_state.policy_reason = policy_reason
            existing_state.action_taken = action_taken
            existing_state.reason = reason
            existing_state.reasoning = reasoning
            existing_state.thought_process = json.loads(json.dumps(thought_process, default=str))
        else:
            # Create new ticket state
            ticket_state = TicketState(
                ticket_id=ticket.id,
                problems=problems,
                policy_name=policy_name,
                policy_desc=policy_desc,
                policy_reason=policy_reason,
                action_taken=action_taken,
                reason=reason,
                reasoning=reasoning,
                thought_process=json.loads(json.dumps(thought_process, default=str))  # Handle serialization
            )
            db.add(ticket_state)
            
        db.commit()
        print(f"Successfully saved/updated ticket {ticket_data['ticket_id']} in database")
        
        return ticket
    except Exception as e:
        db.rollback()
        print(f"Error saving ticket state to database: {str(e)}")
        raise e
    finally:
        db.close()

# Initialize database
if __name__ == "__main__":
    create_tables()
    print("Database tables created successfully!")
