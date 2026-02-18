from __future__ import annotations

from typing import List, Optional

from sqlalchemy.orm import Session
from datetime import datetime
from sqlalchemy import desc
from sqlalchemy.exc import OperationalError
import time

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
    last_error: Optional[OperationalError] = None
    for attempt in range(3):
        try:
            message = ChatMessage(conversation_id=conversation.id, role=role, content=content)
            db.add(message)
            conversation.updated_at = datetime.utcnow()
            if conversation.archived_at is not None:
                conversation.archived_at = None
            if role == "user" and not conversation.title:
                title = (content or "").strip().replace("\n", " ")
                if title:
                    conversation.title = (title[:80] + "…") if len(title) > 80 else title
            db.add(conversation)
            db.commit()
            db.refresh(message)
            return message
        except OperationalError as exc:
            db.rollback()
            last_error = exc
            if "locked" not in str(exc).lower():
                raise
            time.sleep(0.2 * (attempt + 1))
    if last_error is not None:
        raise last_error
    raise OperationalError("DB error", None, None)


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
