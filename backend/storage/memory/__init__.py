"""
Three-Layer Memory System for MyCasa Pro
Implements PARA framework with memory decay and automated extraction
"""
from .manager import MemoryManager, get_memory_manager
from .schemas import (
    AtomicFact,
    Entity,
    MemoryContext,
    ConversationLog,
    FactCategory,
    FactStatus,
    DecayTier,
    PARACategory,
    EntityNotFoundError,
    MemoryWriteError,
    CorruptedDataError,
    ValidationError,
    SearchIndexError,
    validate_fact,
    validate_entity_id,
    calculate_decay_tier,
)

__all__ = [
    # Core classes
    "MemoryManager",
    "get_memory_manager",
    "AtomicFact",
    "Entity",
    "MemoryContext",
    "ConversationLog",
    # Type aliases
    "FactCategory",
    "FactStatus",
    "DecayTier",
    "PARACategory",
    # Exceptions
    "EntityNotFoundError",
    "MemoryWriteError",
    "CorruptedDataError",
    "ValidationError",
    "SearchIndexError",
    # Utilities
    "validate_fact",
    "validate_entity_id",
    "calculate_decay_tier",
]

__version__ = "1.0.0"
