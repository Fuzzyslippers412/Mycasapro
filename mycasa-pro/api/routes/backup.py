from fastapi import APIRouter, HTTPException
from pathlib import Path
import shutil
from datetime import datetime

router = APIRouter(prefix="/backup", tags=["Backup"])

@router.post("/create")
async def create_backup():
    base = Path(__file__).parent.parent.parent
    data_dir = base / "data"
    db_path = data_dir / "mycasa.db"
    if not db_path.exists():
        raise HTTPException(status_code=404, detail="Database not found")
    backups = data_dir / "backups"
    backups.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = backups / f"mycasa_{stamp}.db"
    shutil.copy2(db_path, dest)
    return {"success": True, "backup": str(dest)}
