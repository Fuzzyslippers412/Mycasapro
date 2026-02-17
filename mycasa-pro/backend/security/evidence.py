"""
Evidence Bundle System
Stores documents separately from prompts to prevent injection
"""
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
import json

from .schemas import EvidenceItem, EvidenceBundle


logger = logging.getLogger(__name__)


class EvidenceBundleManager:
    """
    Manages evidence bundles

    Documents are stored separately and accessed by reference only
    This prevents prompt injection via document concatenation
    """

    def __init__(self, storage_path: str = "memory/evidence"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # In-memory cache
        self._bundles: Dict[str, EvidenceBundle] = {}

        logger.info(f"EvidenceBundleManager initialized at {storage_path}")

    def create_bundle(self, session_id: str, created_by: str) -> EvidenceBundle:
        """
        Create a new evidence bundle

        Args:
            session_id: Session ID
            created_by: Agent ID

        Returns:
            Empty EvidenceBundle
        """
        bundle = EvidenceBundle(
            session_id=session_id,
            created_by=created_by
        )

        self._bundles[bundle.id] = bundle
        logger.info(f"Created evidence bundle: {bundle.id}")

        return bundle

    def add_evidence(
        self,
        bundle_id: str,
        content: str,
        source: str,
        content_type: str = "text/plain"
    ) -> Optional[str]:
        """
        Add evidence item to bundle

        Args:
            bundle_id: Bundle ID
            content: Evidence content
            source: Source of evidence
            content_type: Content MIME type

        Returns:
            Evidence item ID or None if failed
        """
        bundle = self._bundles.get(bundle_id)
        if not bundle:
            logger.error(f"Bundle not found: {bundle_id}")
            return None

        item = EvidenceItem(
            content=content,
            content_type=content_type,
            source=source
        )

        bundle.add_item(item)
        logger.info(f"Added evidence {item.id} to bundle {bundle_id}")

        return item.id

    def get_evidence(self, bundle_id: str, item_id: str) -> Optional[str]:
        """
        Get evidence content by reference

        Args:
            bundle_id: Bundle ID
            item_id: Evidence item ID

        Returns:
            Content or None if not found
        """
        bundle = self._bundles.get(bundle_id)
        if not bundle:
            return None

        item = bundle.get_item(item_id)
        if not item:
            return None

        # Verify integrity
        if not item.verify_integrity():
            logger.warning(f"Evidence integrity check failed: {item_id}")
            return None

        return item.content

    def get_references(self, bundle_id: str) -> List[Dict[str, str]]:
        """
        Get evidence references (not content)

        Args:
            bundle_id: Bundle ID

        Returns:
            List of reference dicts
        """
        bundle = self._bundles.get(bundle_id)
        if not bundle:
            return []

        return bundle.get_references()

    def persist_bundle(self, bundle_id: str) -> bool:
        """
        Persist bundle to disk

        Args:
            bundle_id: Bundle ID

        Returns:
            Success boolean
        """
        bundle = self._bundles.get(bundle_id)
        if not bundle:
            return False

        try:
            file_path = self.storage_path / f"{bundle_id}.json"
            with open(file_path, 'w') as f:
                json.dump(bundle.to_dict(), f, indent=2)

            logger.info(f"Persisted bundle: {bundle_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to persist bundle {bundle_id}: {e}")
            return False

    def load_bundle(self, bundle_id: str) -> Optional[EvidenceBundle]:
        """
        Load bundle from disk

        Args:
            bundle_id: Bundle ID

        Returns:
            EvidenceBundle or None
        """
        # Check cache first
        if bundle_id in self._bundles:
            return self._bundles[bundle_id]

        # Load from disk
        try:
            file_path = self.storage_path / f"{bundle_id}.json"
            if not file_path.exists():
                return None

            with open(file_path, 'r') as f:
                data = json.load(f)

            bundle = EvidenceBundle.from_dict(data)
            self._bundles[bundle_id] = bundle

            logger.info(f"Loaded bundle: {bundle_id}")
            return bundle

        except Exception as e:
            logger.error(f"Failed to load bundle {bundle_id}: {e}")
            return None


# Global instance
_evidence_manager: Optional[EvidenceBundleManager] = None


def get_evidence_manager() -> EvidenceBundleManager:
    """Get global evidence manager instance"""
    global _evidence_manager
    if _evidence_manager is None:
        _evidence_manager = EvidenceBundleManager()
    return _evidence_manager
