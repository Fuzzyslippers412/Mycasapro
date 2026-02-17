"""
Conversation Manager - Database persistence for agent chat history
Provides robust CRUD operations with error handling and validation
"""
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from uuid import uuid4
import logging
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy import desc, func

from .models import ConversationDB, MessageDB
from .database import get_db, SessionLocal

logger = logging.getLogger(__name__)


class ConversationError(Exception):
    """Base exception for conversation-related errors"""
    pass


class ConversationNotFoundError(ConversationError):
    """Raised when a conversation is not found"""
    pass


class MessageNotFoundError(ConversationError):
    """Raised when a message is not found"""
    pass


class ConversationManager:
    """
    Manages conversation history with database persistence

    Provides:
    - Conversation CRUD operations
    - Message CRUD operations
    - Search and filtering
    - Statistics and analytics
    - Archival and cleanup
    """

    def __init__(self, db: Optional[Session] = None):
        """
        Initialize conversation manager

        Args:
            db: Optional SQLAlchemy session. If not provided, will create new sessions for each operation.
        """
        self._external_session = db is not None
        self._db = db

    def _get_session(self) -> Session:
        """Get database session (create if not provided)"""
        if self._db is not None:
            return self._db
        return SessionLocal()

    def _close_session(self, db: Session):
        """Close session if we created it"""
        if not self._external_session and db is not None:
            db.close()

    # ==================== CONVERSATION OPERATIONS ====================

    def create_conversation(
        self,
        agent_id: str,
        user_id: str = "lamido",
        title: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a new conversation

        Args:
            agent_id: Agent identifier
            user_id: User identifier
            title: Optional conversation title
            context: Optional metadata/context

        Returns:
            Dictionary with conversation data

        Raises:
            ConversationError: If creation fails
        """
        db = self._get_session()
        try:
            conversation_id = f"conv_{uuid4().hex[:16]}"

            conversation = ConversationDB(
                conversation_id=conversation_id,
                agent_id=agent_id,
                user_id=user_id,
                title=title,
                context=context or {},
                status="active",
                message_count=0,
                total_tokens=0
            )

            db.add(conversation)
            db.commit()
            db.refresh(conversation)

            logger.info(f"Created conversation {conversation_id} for agent {agent_id}")

            return self._conversation_to_dict(conversation)

        except IntegrityError as e:
            db.rollback()
            logger.error(f"Failed to create conversation: {e}")
            raise ConversationError(f"Conversation creation failed: {e}")
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Database error creating conversation: {e}")
            raise ConversationError(f"Database error: {e}")
        finally:
            self._close_session(db)

    def get_conversation(self, conversation_id: str) -> Dict[str, Any]:
        """
        Get conversation by ID

        Args:
            conversation_id: Conversation identifier

        Returns:
            Dictionary with conversation data

        Raises:
            ConversationNotFoundError: If conversation doesn't exist
        """
        db = self._get_session()
        try:
            conversation = db.query(ConversationDB).filter(
                ConversationDB.conversation_id == conversation_id
            ).first()

            if not conversation:
                raise ConversationNotFoundError(f"Conversation {conversation_id} not found")

            return self._conversation_to_dict(conversation)

        except SQLAlchemyError as e:
            logger.error(f"Database error getting conversation: {e}")
            raise ConversationError(f"Database error: {e}")
        finally:
            self._close_session(db)

    def list_conversations(
        self,
        agent_id: Optional[str] = None,
        user_id: Optional[str] = None,
        status: str = "active",
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        List conversations with filtering

        Args:
            agent_id: Filter by agent ID
            user_id: Filter by user ID
            status: Filter by status (active, archived, deleted)
            limit: Maximum number of results
            offset: Pagination offset

        Returns:
            List of conversation dictionaries
        """
        db = self._get_session()
        try:
            query = db.query(ConversationDB)

            if agent_id:
                query = query.filter(ConversationDB.agent_id == agent_id)
            if user_id:
                query = query.filter(ConversationDB.user_id == user_id)
            if status:
                query = query.filter(ConversationDB.status == status)

            query = query.order_by(desc(ConversationDB.updated_at))
            query = query.limit(limit).offset(offset)

            conversations = query.all()

            return [self._conversation_to_dict(c) for c in conversations]

        except SQLAlchemyError as e:
            logger.error(f"Database error listing conversations: {e}")
            raise ConversationError(f"Database error: {e}")
        finally:
            self._close_session(db)

    def update_conversation(
        self,
        conversation_id: str,
        title: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        status: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update conversation metadata

        Args:
            conversation_id: Conversation identifier
            title: New title
            context: New context (will be merged with existing)
            status: New status

        Returns:
            Updated conversation dictionary

        Raises:
            ConversationNotFoundError: If conversation doesn't exist
        """
        db = self._get_session()
        try:
            conversation = db.query(ConversationDB).filter(
                ConversationDB.conversation_id == conversation_id
            ).first()

            if not conversation:
                raise ConversationNotFoundError(f"Conversation {conversation_id} not found")

            if title is not None:
                conversation.title = title
            if context is not None:
                # Merge context
                existing_context = conversation.context or {}
                existing_context.update(context)
                conversation.context = existing_context
            if status is not None:
                conversation.status = status
                if status == "archived":
                    conversation.archived_at = datetime.utcnow()

            conversation.updated_at = datetime.utcnow()

            db.commit()
            db.refresh(conversation)

            logger.info(f"Updated conversation {conversation_id}")

            return self._conversation_to_dict(conversation)

        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Database error updating conversation: {e}")
            raise ConversationError(f"Database error: {e}")
        finally:
            self._close_session(db)

    def archive_conversation(self, conversation_id: str) -> Dict[str, Any]:
        """Archive a conversation"""
        return self.update_conversation(conversation_id, status="archived")

    def delete_conversation(self, conversation_id: str, soft: bool = True) -> bool:
        """
        Delete a conversation

        Args:
            conversation_id: Conversation identifier
            soft: If True, mark as deleted. If False, permanently delete.

        Returns:
            True if deleted successfully
        """
        db = self._get_session()
        try:
            if soft:
                # Soft delete - mark as deleted
                self.update_conversation(conversation_id, status="deleted")
                logger.info(f"Soft deleted conversation {conversation_id}")
            else:
                # Hard delete - permanently remove
                conversation = db.query(ConversationDB).filter(
                    ConversationDB.conversation_id == conversation_id
                ).first()

                if not conversation:
                    raise ConversationNotFoundError(f"Conversation {conversation_id} not found")

                # Delete messages first (cascade should handle this, but explicit is better)
                db.query(MessageDB).filter(
                    MessageDB.conversation_id == conversation_id
                ).delete()

                db.delete(conversation)
                db.commit()

                logger.info(f"Hard deleted conversation {conversation_id}")

            return True

        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Database error deleting conversation: {e}")
            raise ConversationError(f"Database error: {e}")
        finally:
            self._close_session(db)

    # ==================== MESSAGE OPERATIONS ====================

    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        tokens: int = 0,
        model_used: Optional[str] = None,
        latency_ms: Optional[int] = None,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        tool_results: Optional[List[Dict[str, Any]]] = None,
        error: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Add a message to a conversation

        Args:
            conversation_id: Conversation identifier
            role: Message role (user, assistant, system)
            content: Message content
            tokens: Token count
            model_used: LLM model used
            latency_ms: Response latency in milliseconds
            tool_calls: List of tool calls made
            tool_results: List of tool results
            error: Error message if generation failed

        Returns:
            Dictionary with message data

        Raises:
            ConversationNotFoundError: If conversation doesn't exist
        """
        db = self._get_session()
        try:
            # Verify conversation exists
            conversation = db.query(ConversationDB).filter(
                ConversationDB.conversation_id == conversation_id
            ).first()

            if not conversation:
                raise ConversationNotFoundError(f"Conversation {conversation_id} not found")

            message_id = f"msg_{uuid4().hex[:16]}"

            message = MessageDB(
                message_id=message_id,
                conversation_id=conversation_id,
                role=role,
                content=content,
                tokens=tokens,
                model_used=model_used,
                latency_ms=latency_ms,
                tool_calls=tool_calls or [],
                tool_results=tool_results or [],
                error=error,
                retry_count=0
            )

            db.add(message)
            db.commit()
            db.refresh(message)

            logger.debug(f"Added {role} message to conversation {conversation_id}")

            return self._message_to_dict(message)

        except IntegrityError as e:
            db.rollback()
            logger.error(f"Failed to add message: {e}")
            raise ConversationError(f"Message creation failed: {e}")
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Database error adding message: {e}")
            raise ConversationError(f"Database error: {e}")
        finally:
            self._close_session(db)

    def get_messages(
        self,
        conversation_id: str,
        limit: int = 100,
        offset: int = 0,
        include_deleted: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get messages for a conversation

        Args:
            conversation_id: Conversation identifier
            limit: Maximum number of messages
            offset: Pagination offset
            include_deleted: Include soft-deleted messages

        Returns:
            List of message dictionaries (oldest first)
        """
        db = self._get_session()
        try:
            query = db.query(MessageDB).filter(
                MessageDB.conversation_id == conversation_id
            )

            if not include_deleted:
                query = query.filter(MessageDB.deleted_at.is_(None))

            query = query.order_by(MessageDB.created_at.asc(), MessageDB.id.asc())
            query = query.limit(limit).offset(offset)

            messages = query.all()

            return [self._message_to_dict(m) for m in messages]

        except SQLAlchemyError as e:
            logger.error(f"Database error getting messages: {e}")
            raise ConversationError(f"Database error: {e}")
        finally:
            self._close_session(db)

    def delete_message(self, message_id: str, soft: bool = True) -> bool:
        """
        Delete a message

        Args:
            message_id: Message identifier
            soft: If True, soft delete. If False, hard delete.

        Returns:
            True if deleted successfully
        """
        db = self._get_session()
        try:
            message = db.query(MessageDB).filter(
                MessageDB.message_id == message_id
            ).first()

            if not message:
                raise MessageNotFoundError(f"Message {message_id} not found")

            if soft:
                message.deleted_at = datetime.utcnow()
                db.commit()
                logger.debug(f"Soft deleted message {message_id}")
            else:
                db.delete(message)
                db.commit()
                logger.debug(f"Hard deleted message {message_id}")

            return True

        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Database error deleting message: {e}")
            raise ConversationError(f"Database error: {e}")
        finally:
            self._close_session(db)

    # ==================== SEARCH AND ANALYTICS ====================

    def search_conversations(
        self,
        agent_id: str,
        user_id: str,
        search_term: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search conversations by content

        Args:
            agent_id: Agent identifier
            user_id: User identifier
            search_term: Search term
            limit: Maximum results

        Returns:
            List of matching conversations with metadata
        """
        db = self._get_session()
        try:
            # Use the database function for efficient search
            from sqlalchemy import text

            result = db.execute(
                text("""
                    SELECT * FROM search_conversations(:agent_id, :user_id, :search_term, :limit)
                """),
                {
                    "agent_id": agent_id,
                    "user_id": user_id,
                    "search_term": search_term,
                    "limit": limit
                }
            )

            return [dict(row) for row in result]

        except SQLAlchemyError as e:
            logger.error(f"Database error searching conversations: {e}")
            raise ConversationError(f"Database error: {e}")
        finally:
            self._close_session(db)

    def get_conversation_stats(self, agent_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get conversation statistics

        Args:
            agent_id: Optional agent ID to filter by

        Returns:
            Dictionary with statistics
        """
        db = self._get_session()
        try:
            query = db.query(
                func.count(ConversationDB.id).label('total_conversations'),
                func.count(func.distinct(ConversationDB.user_id)).label('unique_users'),
                func.sum(ConversationDB.message_count).label('total_messages'),
                func.sum(ConversationDB.total_tokens).label('total_tokens'),
                func.avg(ConversationDB.message_count).label('avg_messages_per_conversation')
            )

            if agent_id:
                query = query.filter(ConversationDB.agent_id == agent_id)

            query = query.filter(ConversationDB.status == 'active')

            result = query.first()

            return {
                'total_conversations': result.total_conversations or 0,
                'unique_users': result.unique_users or 0,
                'total_messages': result.total_messages or 0,
                'total_tokens': result.total_tokens or 0,
                'avg_messages_per_conversation': float(result.avg_messages_per_conversation or 0)
            }

        except SQLAlchemyError as e:
            logger.error(f"Database error getting stats: {e}")
            raise ConversationError(f"Database error: {e}")
        finally:
            self._close_session(db)

    # ==================== UTILITY METHODS ====================

    @staticmethod
    def _conversation_to_dict(conversation: ConversationDB) -> Dict[str, Any]:
        """Convert ConversationDB to dictionary"""
        return {
            'conversation_id': conversation.conversation_id,
            'agent_id': conversation.agent_id,
            'user_id': conversation.user_id,
            'title': conversation.title,
            'context': conversation.context,
            'status': conversation.status,
            'message_count': conversation.message_count,
            'total_tokens': conversation.total_tokens,
            'created_at': conversation.created_at.isoformat() if conversation.created_at else None,
            'updated_at': conversation.updated_at.isoformat() if conversation.updated_at else None,
            'archived_at': conversation.archived_at.isoformat() if conversation.archived_at else None
        }

    @staticmethod
    def _message_to_dict(message: MessageDB) -> Dict[str, Any]:
        """Convert MessageDB to dictionary"""
        return {
            'message_id': message.message_id,
            'conversation_id': message.conversation_id,
            'role': message.role,
            'content': message.content,
            'tokens': message.tokens,
            'model_used': message.model_used,
            'latency_ms': message.latency_ms,
            'tool_calls': message.tool_calls,
            'tool_results': message.tool_results,
            'error': message.error,
            'retry_count': message.retry_count,
            'created_at': message.created_at.isoformat() if message.created_at else None,
            'deleted_at': message.deleted_at.isoformat() if message.deleted_at else None
        }


# ==================== GLOBAL INSTANCE ====================

_conversation_manager: Optional[ConversationManager] = None


def get_conversation_manager(db: Optional[Session] = None) -> ConversationManager:
    """Get global conversation manager instance"""
    global _conversation_manager
    if _conversation_manager is None or db is not None:
        _conversation_manager = ConversationManager(db=db)
    return _conversation_manager
