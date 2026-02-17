"""
MyCasa Pro API - Google (gog) Setup Routes
Handles OAuth credentials verification and setup for Gmail, Calendar, etc.
"""
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Optional
from pathlib import Path
import subprocess
import json
import shutil

router = APIRouter(prefix="/google", tags=["Google"])

# gog credentials path
GOG_CONFIG_DIR = Path.home() / "Library" / "Application Support" / "gogcli"
GOG_CREDENTIALS_PATH = GOG_CONFIG_DIR / "credentials.json"


class GoogleStatus(BaseModel):
    credentials_exist: bool
    credentials_path: str
    accounts: list[str]
    services_available: list[str]
    auth_status: str  # "not_configured" | "credentials_only" | "authenticated"


class AuthAddRequest(BaseModel):
    email: str


class AuthAddResponse(BaseModel):
    success: bool
    message: str
    auth_url: Optional[str] = None
    needs_browser: bool = False


# ============ STATUS ============

@router.get("/status", response_model=GoogleStatus)
async def get_google_status():
    """
    Get Google/gog setup status.
    Checks if credentials exist and if accounts are authenticated.
    """
    accounts = []
    services = []
    auth_status = "not_configured"
    
    credentials_exist = GOG_CREDENTIALS_PATH.exists()
    
    if credentials_exist:
        auth_status = "credentials_only"
        
        # Check auth status via gog
        try:
            result = subprocess.run(
                ["gog", "auth", "status", "--plain"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                # Parse the output to find accounts
                lines = result.stdout.strip().split("\n")
                for line in lines:
                    if "@" in line and "account" in line.lower():
                        # Extract email from line like "account\tyour@gmail.com"
                        parts = line.split("\t")
                        if len(parts) >= 2:
                            accounts.append(parts[1])
                
                if accounts:
                    auth_status = "authenticated"
                    # Check which services are available
                    services = ["gmail", "calendar", "drive", "contacts", "sheets", "docs"]
                    
        except subprocess.TimeoutExpired:
            pass
        except Exception as e:
            print(f"[GOOGLE] Error checking auth status: {e}")
    
    return GoogleStatus(
        credentials_exist=credentials_exist,
        credentials_path=str(GOG_CREDENTIALS_PATH),
        accounts=accounts,
        services_available=services,
        auth_status=auth_status,
    )


# ============ CREDENTIALS UPLOAD ============

@router.post("/credentials/upload")
async def upload_credentials(file: UploadFile = File(...)):
    """
    Upload OAuth credentials.json file from Google Cloud Console.
    This file is required before authenticating accounts.
    """
    if not file.filename or not file.filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="File must be a .json file")
    
    try:
        content = await file.read()
        
        # Validate it's proper JSON with required fields
        data = json.loads(content)
        
        # Check for OAuth credentials structure
        if "installed" not in data and "web" not in data:
            raise HTTPException(
                status_code=400, 
                detail="Invalid credentials file. Must contain 'installed' or 'web' OAuth client configuration."
            )
        
        # Ensure directory exists
        GOG_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        
        # Backup existing if present
        if GOG_CREDENTIALS_PATH.exists():
            backup_path = GOG_CREDENTIALS_PATH.with_suffix(".json.bak")
            shutil.copy(GOG_CREDENTIALS_PATH, backup_path)
        
        # Write new credentials
        GOG_CREDENTIALS_PATH.write_bytes(content)
        
        return {
            "success": True,
            "message": "Credentials uploaded successfully",
            "path": str(GOG_CREDENTIALS_PATH),
        }
        
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON file")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save credentials: {str(e)}")


@router.get("/credentials/check")
async def check_credentials():
    """
    Check if credentials.json exists and is valid.
    Returns instructions if not configured.
    """
    if not GOG_CREDENTIALS_PATH.exists():
        return {
            "configured": False,
            "message": "No credentials file found",
            "instructions": [
                "1. Go to Google Cloud Console: https://console.cloud.google.com/apis/credentials",
                "2. Create a new OAuth 2.0 Client ID (Desktop application)",
                "3. Download the credentials.json file",
                "4. Upload it here or place it at: " + str(GOG_CREDENTIALS_PATH),
            ],
            "console_url": "https://console.cloud.google.com/apis/credentials",
        }
    
    try:
        data = json.loads(GOG_CREDENTIALS_PATH.read_text())
        client_type = "installed" if "installed" in data else "web"
        client_id = data.get(client_type, {}).get("client_id", "unknown")
        
        return {
            "configured": True,
            "client_type": client_type,
            "client_id": client_id[:30] + "..." if len(client_id) > 30 else client_id,
            "path": str(GOG_CREDENTIALS_PATH),
        }
    except Exception as e:
        return {
            "configured": False,
            "message": f"Invalid credentials file: {str(e)}",
        }


# ============ AUTHENTICATION ============

@router.post("/auth/add", response_model=AuthAddResponse)
async def add_google_account(request: AuthAddRequest):
    """
    Initiate OAuth flow to add a Google account.
    Returns the auth URL to open in browser.
    """
    if not GOG_CREDENTIALS_PATH.exists():
        raise HTTPException(
            status_code=400,
            detail="Credentials not configured. Upload credentials.json first."
        )
    
    try:
        # Run gog auth add with --no-input to get the URL
        result = subprocess.run(
            ["gog", "auth", "add", request.email, "--no-input"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        output = result.stdout + result.stderr
        
        # Look for auth URL in output
        auth_url = None
        for line in output.split("\n"):
            if "http" in line and "google" in line:
                # Extract URL
                import re
                urls = re.findall(r'https?://[^\s<>"]+', line)
                if urls:
                    auth_url = urls[0]
                    break
        
        if auth_url:
            return AuthAddResponse(
                success=True,
                message="Open the URL below in your browser to authenticate",
                auth_url=auth_url,
                needs_browser=True,
            )
        
        # If no URL, maybe already authenticated
        if "already" in output.lower() or result.returncode == 0:
            return AuthAddResponse(
                success=True,
                message=f"Account {request.email} is already authenticated",
                needs_browser=False,
            )
        
        return AuthAddResponse(
            success=False,
            message=f"Authentication failed: {output[:500]}",
            needs_browser=False,
        )
        
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Authentication request timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Authentication error: {str(e)}")


@router.post("/auth/complete")
async def complete_auth(email: str, code: str):
    """
    Complete OAuth flow with the authorization code.
    (For cases where manual code entry is needed)
    """
    # This would be used if we need to handle the callback manually
    # For now, gog handles this through the browser redirect
    return {"success": True, "message": "Use the browser flow to complete authentication"}


@router.get("/auth/verify")
async def verify_google_auth(email: str):
    """
    Verify that a Google account is properly authenticated.
    Attempts a simple API call to confirm.
    """
    try:
        # Try to list labels as a simple test
        result = subprocess.run(
            ["gog", "gmail", "labels", "--account", email, "--json"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            labels = json.loads(result.stdout)
            return {
                "authenticated": True,
                "email": email,
                "test": "gmail_labels",
                "label_count": len(labels) if isinstance(labels, list) else 0,
            }
        
        return {
            "authenticated": False,
            "email": email,
            "error": result.stderr[:200] if result.stderr else "Unknown error",
        }
        
    except Exception as e:
        return {
            "authenticated": False,
            "email": email,
            "error": str(e),
        }


# ============ SERVICES ============

@router.get("/services")
async def list_google_services():
    """
    List available Google services that can be used.
    """
    return {
        "services": [
            {"id": "gmail", "name": "Gmail", "description": "Read and send emails", "icon": "📧"},
            {"id": "calendar", "name": "Calendar", "description": "Manage events", "icon": "📅"},
            {"id": "drive", "name": "Drive", "description": "Access files", "icon": "📁"},
            {"id": "contacts", "name": "Contacts", "description": "Manage contacts", "icon": "👥"},
            {"id": "sheets", "name": "Sheets", "description": "Read/write spreadsheets", "icon": "📊"},
            {"id": "docs", "name": "Docs", "description": "Access documents", "icon": "📄"},
        ]
    }
