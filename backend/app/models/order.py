from sqlalchemy import Column, String, Float

from app.db.database import Base


class Order(Base):
    __tablename__ = "orders"

    order_id = Column(String, primary_key=True)
    customer_id = Column(String, nullable=False, index=True)
    order_date = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    product_category = Column(String, nullable=False)
    status = Column(String, nullable=False)
