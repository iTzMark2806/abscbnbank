from sqlalchemy import Column, Integer, String, Float, ForeignKey
from database import Base

class Bank(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    email = Column(String)
    pin = Column(String)  # hashed PIN
    balance = Column(Float, default=0.0)
    account_number = Column(String, unique=True, index=True)


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String)
    amount = Column(Float)
    account_id = Column(Integer, ForeignKey("accounts.id"))