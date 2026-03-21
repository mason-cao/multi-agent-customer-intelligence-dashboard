from sqlalchemy import Column, String, Float, Integer

from app.db.database import Base


class Subscription(Base):
    __tablename__ = "subscriptions"

    subscription_id = Column(String, primary_key=True)
    customer_id = Column(String, nullable=False, index=True)
    plan_tier = Column(String, nullable=False)
    mrr = Column(Float, nullable=False)
    start_date = Column(String, nullable=False)
    renewal_date = Column(String, nullable=False)
    payment_method = Column(String, nullable=False)
    payment_failures_90d = Column(Integer, default=0)
    auto_renew = Column(Integer, default=1)
