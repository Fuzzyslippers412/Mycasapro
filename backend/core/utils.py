"""
MyCasa Pro Utilities
"""
import json
import logging
import hashlib
import os
from datetime import datetime
from uuid import uuid4
from typing import Any, Dict, Optional
from pathlib import Path

# Structured JSON logger
class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_obj = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
        }
        if hasattr(record, 'correlation_id'):
            log_obj["correlation_id"] = record.correlation_id
        if hasattr(record, 'user_id'):
            log_obj["user_id"] = record.user_id
        if hasattr(record, 'extra_data'):
            log_obj["data"] = record.extra_data
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_obj)


def setup_logger(name: str = "mycasa", log_file: Optional[str] = None) -> logging.Logger:
    """Set up structured JSON logger"""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Console handler with JSON
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(JSONFormatter())
    logger.addHandler(console_handler)
    
    # File handler if specified
    if log_file:
        try:
            Path(log_file).parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(JSONFormatter())
            logger.addHandler(file_handler)
        except Exception:
            fallback = os.getenv("MYCASA_LOG_FALLBACK", "/tmp/mycasa.log")
            Path(fallback).parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(fallback)
            file_handler.setFormatter(JSONFormatter())
            logger.addHandler(file_handler)
    
    return logger


# Global logger instance
logger = setup_logger("mycasa", os.getenv("MYCASA_LOG_FILE", "data/logs/mycasa.log"))


def generate_correlation_id() -> str:
    """Generate a short correlation ID"""
    return str(uuid4())[:8]


def generate_run_id() -> str:
    """Generate a run ID for a session"""
    return f"run_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{str(uuid4())[:4]}"


def log_action(
    action: str,
    details: Dict[str, Any],
    correlation_id: Optional[str] = None,
    user_id: str = "lamido",
    level: str = "info"
):
    """Log an action with correlation tracking"""
    record = logging.LogRecord(
        name="mycasa",
        level=getattr(logging, level.upper()),
        pathname="",
        lineno=0,
        msg=action,
        args=(),
        exc_info=None
    )
    record.correlation_id = correlation_id or generate_correlation_id()
    record.user_id = user_id
    record.extra_data = details
    logger.handle(record)
    
    return record.correlation_id


def calculate_checksum(file_path: str) -> str:
    """Calculate SHA256 checksum of a file"""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def calculate_data_checksum(data: bytes) -> str:
    """Calculate SHA256 checksum of bytes"""
    return hashlib.sha256(data).hexdigest()


def estimate_cost(model: str, tokens_in: int, tokens_out: int) -> float:
    """Estimate cost for AI model usage"""
    from .constants import MODEL_COSTS
    
    costs = MODEL_COSTS.get(model, {"input": 0.01, "output": 0.03})
    cost = (tokens_in / 1000 * costs["input"]) + (tokens_out / 1000 * costs["output"])
    return round(cost, 6)


def format_currency(amount: float) -> str:
    """Format amount as currency"""
    return f"${amount:,.2f}"


def safe_json_dumps(obj: Any) -> str:
    """Safe JSON serialization with datetime handling"""
    def default(o):
        if isinstance(o, datetime):
            return o.isoformat()
        if hasattr(o, '__dict__'):
            return o.__dict__
        return str(o)
    return json.dumps(obj, default=default)
