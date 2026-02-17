from __future__ import annotations

from typing import List, Optional

from sqlalchemy.orm import Session
from datetime import datetime
from sqlalchemy import desc

from database.models import ChatConversation, ChatMessage


def get_or_create_conversation(
    db: Session,
    user_id: int,
    agent_name: str,
    conversation_id: Optional[str] = None,
) -> ChatConversation:
    if conversation_id:
        convo = (
            db.query(ChatConversation)
            .filter(ChatConversation.id == conversation_id, ChatConversation.user_id == user_id)
            .first()
        )
        if convo:
            return convo

    convo = (
        db.query(ChatConversation)
        .filter(ChatConversation.user_id == user_id, ChatConversation.agent_name == agent_name)
        .order_by(desc(ChatConversation.updated_at))
        .first()
    )
    if convo:
        return convo

    convo = ChatConversation(user_id=user_id, agent_name=agent_name)
    db.add(convo)
    db.commit()
    db.refresh(convo)
    return convo


def add_message(
    db: Session,
    conversation: ChatConversation,
    role: str,
    content: str,
) -> ChatMessage:
    message = ChatMessage(conversation_id=conversation.id, role=role, content=content)
    db.add(message)
    conversation.updated_at = datetime.utcnow()
    db.add(conversation)
    db.commit()
    db.refresh(message)
    return message


def get_history(
    db: Session,
    conversation_id: str,
    limit: int = 50,
) -> List[ChatMessage]:
    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.conversation_id == conversation_id)
        .order_by(ChatMessage.created_at.asc())
        .limit(limit)
        .all()
    )
    return messages
