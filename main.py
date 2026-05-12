from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Annotated
from sqlalchemy.orm import Session
import uuid
import models
from database import engine, SessionLocal
from passlib.context import CryptContext

app = FastAPI()

# This correctly creates the tables in the database
models.Base.metadata.create_all(bind=engine)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_pin(pin: int) -> str:
    return pwd_context.hash(str(pin))

def verify_pin(pin: int, hashed_pin: str) -> bool:
    return pwd_context.verify(str(pin), hashed_pin)

# --- Schemas ---
class AccountCreate(BaseModel):
    name: str
    email: str
    pin: int
    initial_balance: float

class PinRequest(BaseModel):
    pin: int

class AmountRequest(BaseModel):
    amount: float
    pin: int

class TransferRequest(BaseModel):
    receiver_account_number: str
    amount: float
    pin: int

# --- DB Dependency ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]

# --- Routes ---
@app.post("/accounts/")
async def create_account(account: AccountCreate, db: db_dependency):
    acc_number = str(uuid.uuid4())[:10]
    db_account = models.Bank(
        name=account.name,
        email=account.email,
        pin=hash_pin(account.pin), 
        balance=account.initial_balance,
        account_number=acc_number
    )
    db.add(db_account)
    db.commit()
    db.refresh(db_account)
    return {"account_number": acc_number}

@app.post("/accounts/{account_number}/balance")
async def check_balance(account_number: str, req: PinRequest, db: db_dependency):
    account = db.query(models.Bank).filter(models.Bank.account_number == account_number).first()
    if not account or not verify_pin(req.pin, account.pin):
        raise HTTPException(status_code=401, detail="Invalid account or PIN")
    return {"balance": account.balance}

@app.post("/accounts/{account_number}/withdraw")
async def withdraw(account_number: str, req: AmountRequest, db: db_dependency):
    account = db.query(models.Bank).filter(models.Bank.account_number == account_number).first()
    if not account or not verify_pin(req.pin, account.pin):
        raise HTTPException(status_code=401, detail="Invalid account or PIN")
    if account.balance < req.amount:
        raise HTTPException(status_code=400, detail="Insufficient balance")
    account.balance -= req.amount
    db.add(models.Transaction(type="withdraw", amount=req.amount, account_id=account.id))
    db.commit()
    return {"balance": account.balance}

@app.post("/accounts/{account_number}/transfer")
async def transfer(account_number: str, req: TransferRequest, db: db_dependency):
    sender = db.query(models.Bank).filter(models.Bank.account_number == account_number).first()
    receiver = db.query(models.Bank).filter(models.Bank.account_number == req.receiver_account_number).first()
    if not sender or not receiver:
        raise HTTPException(status_code=404, detail="Account not found")
    if not verify_pin(req.pin, sender.pin):
        raise HTTPException(status_code=401, detail="Invalid PIN")
    if sender.balance < req.amount:
        raise HTTPException(status_code=400, detail="Insufficient balance")
    sender.balance -= req.amount
    receiver.balance += req.amount
    db.add(models.Transaction(type="transfer_out", amount=req.amount, account_id=sender.id))
    db.add(models.Transaction(type="transfer_in", amount=req.amount, account_id=receiver.id))
    db.commit()
    return {"message": "Transfer successful"}