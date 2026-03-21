from sqlalchemy import Column, String, Integer, Text

from app.db.database import Base


class Customer(Base):
    __tablename__ = "customers"

    customer_id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    company = Column(String, nullable=False)
    industry = Column(String, nullable=False)
    company_size = Column(String, nullable=False)
    plan_tier = Column(String, nullable=False)
    signup_date = Column(String, nullable=False)
    region = Column(String, nullable=False)
    acquisition_channel = Column(String, nullable=False)
    is_churned = Column(Integer, default=0)
    churned_date = Column(String, nullable=True)
