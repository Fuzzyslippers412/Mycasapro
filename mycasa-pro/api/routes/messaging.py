"""
MyCasa Pro API - Messaging Routes
WhatsApp and other messaging capabilities via Manager agent.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

router = APIRouter(prefix="/messaging", tags=["Messaging"])


# ============ SCHEMAS ============

class SendMessageRequest(BaseModel):
    """Request to send a message"""
    to: str = Field(..., description="Recipient name or phone number")
    message: str = Field(..., description="Message content")
    channel: str = Field(default="whatsapp", description="Messaging channel")
    record_in_secondbrain: bool = Field(default=True, description="Log in SecondBrain")


class NaturalLanguageRequest(BaseModel):
    """Natural language messaging request"""
    request: str = Field(..., description="Natural language request, e.g., 'Send WhatsApp to Anastasia saying hello'")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context")


class Contact(BaseModel):
    """Contact information"""
    name: str
    phone: str
    relation: Optional[str] = None
    jid: Optional[str] = None


# ============ ROUTES ============

@router.get("/contacts")
async def list_contacts() -> List[Contact]:
    """
    List all known contacts.
    """
    from api.main import get_manager
    
    manager = get_manager()
    contacts = manager.get_contacts()
    
    return [Contact(**c) for c in contacts]


@router.get("/contacts/search")
async def search_contact(query: str) -> Optional[Contact]:
    """
    Search for a contact by name or phone number.
    """
    from api.main import get_manager
    
    manager = get_manager()
    contact = manager.lookup_contact(query)
    
    if contact:
        return Contact(**contact)
    return None


@router.post("/send")
async def send_message(request: SendMessageRequest):
    """
    Send a message to a contact.
    
    Example:
    ```json
    {
        "to": "Anastasia",
        "message": "Hello! How are you?"
    }
    ```
    """
    from api.main import get_manager
    
    manager = get_manager()
    
    if request.channel != "whatsapp":
        raise HTTPException(status_code=400, detail=f"Channel '{request.channel}' not yet supported")
    
    result = manager.send_whatsapp(
        to=request.to,
        message=request.message,
        record_in_secondbrain=request.record_in_secondbrain
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Send failed"))
    
    return result


@router.post("/natural")
async def natural_language_message(request: NaturalLanguageRequest):
    """
    Handle a natural language messaging request.
    
    Example:
    ```json
    {
        "request": "Send a WhatsApp to Anastasia saying hello, how is the baby?"
    }
    ```
    """
    from api.main import get_manager
    
    manager = get_manager()
    
    result = manager.handle_messaging_request(
        request=request.request,
        context=request.context
    )
    
    if not result.get("success"):
        raise HTTPException(
            status_code=400,
            detail={
                "error": result.get("error"),
                "suggestion": result.get("suggestion"),
                "available_contacts": result.get("available_contacts")
            }
        )
    
    return result


@router.get("/status")
async def messaging_status():
    """
    Get messaging system status.
    """
    from connectors.whatsapp import WhatsAppConnector
    
    wa = WhatsAppConnector()
    status = await wa.health_check("tenkiang_household")
    
    return {
        "whatsapp": {
            "status": status.value,
            "contacts_loaded": len(wa.get_all_contacts())
        }
    }
