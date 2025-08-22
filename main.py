from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID, uuid4
from datetime import datetime, timezone

from sqlalchemy import create_engine, Column, ForeignKey, Text, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import sessionmaker, Session, relationship, declarative_base

import uvicorn
app = FastAPI()

DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/postgres"

engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class Chat(Base):
    __tablename__ = "chat"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False)
    name = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    conversations = relationship("Conversation", back_populates="chat", cascade="all, delete")
    files = relationship("File", back_populates="chat", cascade="all, delete")


class Conversation(Base):
    __tablename__ = "conversation"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False)
    role = Column(Text, nullable=True)
    content = Column(Text, nullable=True)
    chat_id = Column(PG_UUID(as_uuid=True), ForeignKey("chat.id"), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    chat = relationship("Chat", back_populates="conversations")


class File(Base):
    __tablename__ = "files"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False)
    name = Column(Text, nullable=True)
    path = Column(Text, nullable=True)
    file_type = Column(Text, nullable=True)
    chat_id = Column(PG_UUID(as_uuid=True), ForeignKey("chat.id"), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    chat = relationship("Chat", back_populates="files")

#Base.metadata.create_all(bind=engine)

class ChatCreate(BaseModel):
    name: str

class ChatOut(BaseModel):
    id: UUID
    name: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }

class ChatSummary(BaseModel):
    id: UUID
    name: Optional[str]

    model_config = {
        "from_attributes": True
    }

class ConversationCreate(BaseModel):
    role: str
    content: str
    chat_id: UUID

class ConversationOut(BaseModel):
    id: UUID
    role: str
    content: str
    chat_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

class historyout(BaseModel):
    role: str
    content: str

    model_config = {"from_attributes": True}

class UserMessageInput(BaseModel):
    message: str

class FileUpload(BaseModel):
    name: str
    path: str
    file_type: str

    model_config = {"from_attributes": True}

class FileOut(BaseModel):
    id: UUID
    name: str
    path: str
    file_type: str
    chat_id: UUID

    model_config = {"from_attributes": True}


def rag_reply(user_message :str) -> str:
    return "recieved and returned"

@app.post("/chat", response_model=ChatOut)
def create_chat(chat: ChatCreate, db: Session = Depends(get_db)):
    new_chat = Chat(name=chat.name)
    db.add(new_chat)
    db.commit()
    db.refresh(new_chat)
    return new_chat

@app.get("/allchats", response_model=List[ChatSummary])
def get_all_chats(db: Session = Depends(get_db)):
    chats = db.query(Chat).all()
    return chats

@app.post("/chat/{chat_id}", response_model=List[ConversationOut])
def handle_chat_message(chat_id: UUID, user_input: UserMessageInput, db: Session = Depends(get_db)):
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    user_msg = Conversation(
        role="user",
        content=user_input.message,
        chat_id=chat_id
    )
    db.add(user_msg)
    db.commit()
    db.refresh(user_msg)

    reply_text = rag_reply(user_input.message)

    system_msg = Conversation(
        role="system",
        content=reply_text,
        chat_id=chat_id
    )
    db.add(system_msg)

    chat.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(system_msg)

    return [user_msg, system_msg]


@app.get("/chathistory/{chat_id}", response_model= List[historyout])
def chathistory(chat_id: UUID, db: Session = Depends(get_db)):
    chats = db.query(Conversation).filter(Conversation.chat_id == chat_id).all()
    return chats

@app.post("/addfile/{chat_id}", response_model= FileOut)
def addfile(chat_id: UUID, file: FileUpload, db: Session = Depends(get_db)):
    new_file = File(name=file.name,path=file.path,file_type=file.file_type,chat_id = chat_id)
    db.add(new_file)
    db.commit()
    db.refresh(new_file)
    return new_file

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)