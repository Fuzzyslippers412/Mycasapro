# Legacy Code

This directory contains legacy code that is **not part of the primary UI**.

## Contents

### `streamlit/`
Original Streamlit pages from early development. These are **deprecated** and retained only for reference or internal dev use.

**Do not use these for production.** The primary UI is the Next.js frontend at `frontend/`.

## Migration Path

If you need functionality from legacy code:
1. Identify the feature in `streamlit/`
2. Implement in `frontend/src/app/` using React/Mantine
3. Ensure it uses API endpoints (no direct DB access)
4. Delete the legacy code after migration is verified
