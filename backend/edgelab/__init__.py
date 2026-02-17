"""
Edge Lab - Postgres-backed, Point-in-Time Financial Prediction System

NON-NEGOTIABLE GUARDRAILS:
1. Evidence Boundary: Every output references snapshot_id + snapshot_hash
2. No External Narrative: No claims without ingested data
3. Determinism: Features deterministic given snapshot_id
4. Auditability: All inputs/outputs stored with hashes
5. Safety: Writes ONLY to edgelab schema
"""

__version__ = "0.1.0"
