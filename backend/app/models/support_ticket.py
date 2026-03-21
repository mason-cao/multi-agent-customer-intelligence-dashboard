from sqlalchemy import Column, String, Text

from app.db.database import Base


class SupportTicket(Base):
    __tablename__ = "support_tickets"

    ticket_id = Column(String, primary_key=True)
    customer_id = Column(String, nullable=False, index=True)
    created_at = Column(String, nullable=False)
    resolved_at = Column(String, nullable=True)
    category = Column(String, nullable=False)
    priority = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    text = Column(Text, nullable=False)
    resolution_status = Column(String, nullable=False)
