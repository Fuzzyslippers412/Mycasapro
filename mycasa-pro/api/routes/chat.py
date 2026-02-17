"""
MyCasa Pro API - Chat Routes
Chat interface with the Manager agent.

This enables conversational interaction with the Manager,
similar to chatting with Galidima via WhatsApp/Clawdbot.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

from config.settings import VAULT_PATH

router = APIRouter(prefix="/chat", tags=["Chat"])

# In-memory conversation store (with SecondBrain persistence)
_conversations: Dict[str, List[Dict[str, Any]]] = {}
_default_conversation_id = "main"
_conversations_loaded_from_sb = False  # Track if we've loaded from SecondBrain


# ============ SCHEMAS ============

class ChatMessage(BaseModel):
    """A single chat message"""
    id: str
    role: str  # "user" or "assistant"
    content: str
    timestamp: str


class SendMessageRequest(BaseModel):
    """Request to send a message to the Manager"""
    message: str = Field(..., description="User message")
    conversation_id: Optional[str] = Field(default=None, description="Conversation ID")


class SendMessageResponse(BaseModel):
    """Response from the Manager"""
    response: str
    message_id: str
    conversation_id: str
    actions_taken: Optional[List[Dict[str, Any]]] = None
    reasoning_log: Optional[List[str]] = Field(
        default=None,
        description="Step-by-step reasoning for transparency (LobeHub-inspired)"
    )


class ConversationHistory(BaseModel):
    """Conversation history"""
    conversation_id: str
    messages: List[ChatMessage]


# ============ HELPER FUNCTIONS ============

def _load_conversations_from_secondbrain() -> None:
    """Load conversations from SecondBrain on first access"""
    global _conversations_loaded_from_sb
    
    if _conversations_loaded_from_sb:
        return
    
    try:
        import yaml
        
        vault_path = VAULT_PATH / "conversations"
        
        if vault_path.exists():
            for conv_file in vault_path.glob("conv_*.md"):
                try:
                    content = conv_file.read_text(encoding="utf-8")
                    
                    # Parse YAML frontmatter
                    if content.startswith("---"):
                        end_idx = content.find("---", 3)
                        if end_idx > 0:
                            frontmatter = yaml.safe_load(content[4:end_idx])
                            body = content[end_idx + 4:].strip()
                            
                            conv_id = frontmatter.get("conversation_id", conv_file.stem)
                            messages = frontmatter.get("messages", [])
                            
                            if conv_id and messages:
                                _conversations[conv_id] = messages
                except Exception:
                    pass  # Skip malformed files
        
        _conversations_loaded_from_sb = True
    except Exception:
        _conversations_loaded_from_sb = True  # Mark as loaded even on error


def _save_conversation_to_secondbrain(conversation_id: str) -> None:
    """Persist conversation to SecondBrain vault"""
    try:
        import yaml
        
        messages = _conversations.get(conversation_id, [])
        if not messages:
            return
        
        vault_path = VAULT_PATH / "conversations"
        vault_path.mkdir(parents=True, exist_ok=True)
        
        # Create/update conversation file
        conv_file = vault_path / f"conv_{conversation_id}.md"
        
        frontmatter = {
            "conversation_id": conversation_id,
            "message_count": len(messages),
            "updated_at": datetime.now().isoformat(),
            "messages": messages,
        }
        
        # Get branch info if exists
        if conversation_id in _conversation_branches:
            frontmatter["branch_info"] = _conversation_branches[conversation_id]
        
        content = f"""---
{yaml.dump(frontmatter, default_flow_style=False, allow_unicode=True)}---

# Conversation: {conversation_id}

*{len(messages)} messages*
"""
        
        conv_file.write_text(content, encoding="utf-8")
    except Exception:
        pass  # Non-blocking persistence


def _get_conversation(conversation_id: str) -> List[Dict[str, Any]]:
    """Get or create a conversation"""
    _load_conversations_from_secondbrain()
    
    if conversation_id not in _conversations:
        _conversations[conversation_id] = []
    return _conversations[conversation_id]


def _add_message(conversation_id: str, role: str, content: str) -> str:
    """Add a message to conversation history"""
    messages = _get_conversation(conversation_id)
    msg_id = str(uuid.uuid4())[:8]
    messages.append({
        "id": msg_id,
        "role": role,
        "content": content,
        "timestamp": datetime.now().isoformat()
    })
    
    # Persist to SecondBrain (non-blocking)
    _save_conversation_to_secondbrain(conversation_id)
    
    return msg_id


def _process_with_manager(user_message: str, conversation_history: List[Dict]) -> Dict[str, Any]:
    """
    Process a user message with the Manager agent.
    
    This is where the Manager "thinks" and responds.
    The Manager has access to shared context from Galidima via SharedContext.
    
    Now includes reasoning_log for transparency (LobeHub-inspired).
    """
    from core.shared_context import get_shared_context
    from api.main import get_manager

    manager = get_manager()
    shared_ctx = get_shared_context()
    response_text = ""
    actions_taken = []
    reasoning_log = []  # Track decision-making steps
    
    # Step 1: Load context
    reasoning_log.append(f"📥 Received message: \"{user_message[:50]}{'...' if len(user_message) > 50 else ''}\"")
    
    # Get shared context for relevant responses
    context = shared_ctx.get_full_context(include_session=True)  # Sync with Clawdbot session history
    reasoning_log.append(f"🧠 Loaded context: {len(context.get('contacts', []))} contacts, {len(context.get('long_term_memory', ''))} chars memory")
    
    # Lowercase for pattern matching
    msg_lower = user_message.lower().strip()
    reasoning_log.append(f"🔍 Analyzing intent...")
    
    # ===============================
    # @MENTION AGENT ROUTING (LLM-powered)
    # ===============================
    import re
    from core.llm import chat_with_agent, get_agent_greeting, AGENT_PERSONAS
    
    # Agent name mapping
    agent_mentions = {
        "@mamadou": "finance",
        "@ousmane": "maintenance", 
        "@aicha": "security",
        "@aïcha": "security",
        "@malik": "contractors",
        "@zainab": "projects",
        "@galidima": "manager",
        "@janitor": "janitor",
        "@mail": "mail",
        "@email": "mail",
    }
    
    # Check for @mentions
    mentioned_agent_id = None
    clean_message = user_message
    
    for mention, agent_id in agent_mentions.items():
        if mention in msg_lower:
            mentioned_agent_id = agent_id
            # Strip all @mentions from the message
            for m in agent_mentions.keys():
                clean_message = re.sub(re.escape(m), '', clean_message, flags=re.IGNORECASE).strip()
            reasoning_log.append(f"✓ Detected @mention: {AGENT_PERSONAS[agent_id]['name']} ({agent_id})")
            break
    
    if mentioned_agent_id:
        persona = AGENT_PERSONAS[mentioned_agent_id]
        reasoning_log.append(f"🔄 Routing to {persona['name']} via LLM...")
        
        # Build context for the agent
        agent_context = {}
        try:
            if mentioned_agent_id == "finance":
                from agents.finance import FinanceAgent
                agent = FinanceAgent()
                agent_context["portfolio"] = agent.get_portfolio_summary()
                agent_context["upcoming_bills"] = agent.get_upcoming_bills(30)
            elif mentioned_agent_id == "maintenance":
                from agents.maintenance import MaintenanceAgent
                agent = MaintenanceAgent()
                agent_context["pending_tasks"] = agent.get_pending_tasks()
            elif mentioned_agent_id == "contractors":
                from agents.contractors import ContractorsAgent
                agent = ContractorsAgent()
                agent_context["contractors"] = agent.get_contractors()
            elif mentioned_agent_id == "projects":
                from agents.projects import ProjectsAgent
                agent = ProjectsAgent()
                agent_context["projects"] = agent.get_active_projects()
        except Exception as e:
            reasoning_log.append(f"⚠️ Context fetch error: {str(e)}")
        
        # Call LLM with agent persona
        try:
            response_text = chat_with_agent(
                agent_id=mentioned_agent_id,
                message=clean_message or "hello",
                context=agent_context,
                conversation_history=conversation_history
            )
            reasoning_log.append(f"✅ {persona['name']} responded via LLM")
        except Exception as e:
            reasoning_log.append(f"❌ LLM error: {str(e)}")
            response_text = f"{persona['emoji']} **{persona['name']}** is having trouble connecting.\n\nError: {str(e)}"
        
        return {
            "response": response_text,
            "actions_taken": actions_taken,
            "reasoning_log": reasoning_log
        }
    
    # ===============================
    # COMMAND PATTERNS
    # ===============================
    
    # 1. Status queries
    if any(phrase in msg_lower for phrase in [
        "what's going on", "whats going on", "what is going on", "status", 
        "what is happening", "system status", "quick status", "update me", 
        "what's up", "whats up", "what is up"
    ]):
        reasoning_log.append("✓ Detected intent: STATUS_QUERY")
        reasoning_log.append("🔄 Calling manager.quick_status()")
        status = manager.quick_status()
        reasoning_log.append(f"📊 Got status with {len(status.get('facts', {}))} fact categories")
        response_text = _format_quick_status(status)
    
    # 2. Full report
    elif any(phrase in msg_lower for phrase in [
        "full report", "detailed status", "full status", "everything"
    ]):
        report = manager.full_system_report()
        response_text = _format_full_report(report)
    
    # 3. WhatsApp messaging
    elif any(phrase in msg_lower for phrase in [
        "send whatsapp", "send a whatsapp", "whatsapp to", "message to",
        "text to", "send message"
    ]):
        reasoning_log.append("✓ Detected intent: SEND_MESSAGE")
        reasoning_log.append("📱 Parsing message request...")
        result = manager.handle_messaging_request(user_message)
        if result.get("success"):
            reasoning_log.append(f"✅ Message sent to {result.get('to')}")
            response_text = f"✅ Message sent to {result.get('to')}!\n\nPreview: \"{result.get('message_preview')}\""
            actions_taken.append({
                "action": "whatsapp_sent",
                "to": result.get("to"),
                "phone": result.get("phone")
            })
        else:
            reasoning_log.append(f"❌ Send failed: {result.get('error')}")
            contacts = result.get("available_contacts", [])
            suggestion = result.get("suggestion", "")
            response_text = f"❌ {result.get('error', 'Failed to send message')}"
            if contacts:
                response_text += f"\n\nAvailable contacts: {', '.join(contacts)}"
            if suggestion:
                response_text += f"\n\n💡 {suggestion}"
    
    # 4. List contacts
    elif any(phrase in msg_lower for phrase in [
        "list contacts", "show contacts", "who can i message", "contacts"
    ]):
        contacts = manager.get_contacts()
        if contacts:
            response_text = "📇 **Contacts:**\n\n"
            for c in contacts:
                response_text += f"• **{c['name']}** ({c.get('relation', 'Contact')}): {c['phone']}\n"
        else:
            response_text = "No contacts found. Add contacts to TOOLS.md."
    
    # 5. Task queries
    elif any(phrase in msg_lower for phrase in [
        "pending task", "task", "todo", "to do", "what needs", "overdue"
    ]):
        reasoning_log.append("✓ Detected intent: TASK_QUERY")
        reasoning_log.append("📋 Querying database for tasks...")
        try:
            from database import get_db
            from database.models import MaintenanceTask
            
            with get_db() as db:
                tasks = db.query(MaintenanceTask).filter(
                    MaintenanceTask.status.in_(["pending", "in_progress"])
                ).order_by(MaintenanceTask.due_date).limit(10).all()
                
                reasoning_log.append(f"📊 Found {len(tasks)} pending tasks")
                if tasks:
                    response_text = "📋 **Pending Tasks:**\n\n"
                    for t in tasks:
                        due = t.due_date.strftime("%b %d") if t.due_date else "No date"
                        response_text += f"• [{t.priority.upper()}] {t.title} - Due: {due}\n"
                else:
                    response_text = "✅ No pending tasks!"
        except Exception as e:
            reasoning_log.append(f"❌ Database error: {e}")
            response_text = f"Could not fetch tasks: {e}"
    
    # 6. Bill queries
    elif any(phrase in msg_lower for phrase in [
        "bill", "upcoming bill", "due bill", "payment"
    ]):
        try:
            from database import get_db
            from database.models import Bill
            
            with get_db() as db:
                bills = db.query(Bill).filter(
                    Bill.status == "pending"
                ).order_by(Bill.due_date).limit(10).all()
                
                if bills:
                    response_text = "💰 **Upcoming Bills:**\n\n"
                    for b in bills:
                        due = b.due_date.strftime("%b %d") if b.due_date else "No date"
                        response_text += f"• {b.name}: ${b.amount:.2f} - Due: {due}\n"
                else:
                    response_text = "✅ No pending bills!"
        except Exception as e:
            response_text = f"Could not fetch bills: {e}"
    
    # 7. Recent activity / what did we do
    elif any(phrase in msg_lower for phrase in [
        "recent activity", "what did we do", "what happened", "recent history",
        "what have you been doing", "today's activity"
    ]):
        recent_memories = context.get("recent_memory", [])
        if recent_memories:
            today = recent_memories[0] if recent_memories else None
            if today:
                response_text = f"📜 **Recent Activity**\n\n{today.get('content', 'No activity recorded')[:2000]}"
            else:
                response_text = "No recent activity recorded yet today."
        else:
            response_text = "No recent activity found."
    
    # 8. Who am I / about user
    elif any(phrase in msg_lower for phrase in [
        "who am i", "about me", "my profile", "user profile"
    ]):
        user_info = context.get("user", "")
        if user_info:
            response_text = f"👤 **User Profile**\n\n{user_info[:1500]}"
        else:
            response_text = "User profile not found."
    
    # 9. What do you know / context
    elif any(phrase in msg_lower for phrase in [
        "what do you know", "your memory", "what do you remember", "context"
    ]):
        memory = context.get("long_term_memory", "")
        response_text = "🧠 **My Knowledge**\n\n"
        response_text += f"I have access to:\n"
        response_text += f"• Long-term memory ({len(memory)} chars)\n"
        response_text += f"• {len(context.get('contacts', []))} contacts\n"
        response_text += f"• {len(context.get('recent_memory', []))} days of recent activity\n"
        response_text += f"\nRecent session messages are also available for context."
        
        # Show a snippet of memory
        if memory:
            response_text += f"\n\n**Memory Snippet:**\n{memory[:500]}..."
    
    # 10. Help
    elif any(phrase in msg_lower for phrase in [
        "help", "what can you do", "commands", "how do i"
    ]):
        response_text = """👋 I'm **Galidima**, your MyCasa Pro Manager.

I share context with the main Clawdbot agent, so I know about your conversations, contacts, and preferences.

**What I can do:**

📊 **Status Reports**
• "What's going on?" - Quick status
• "Full report" - Detailed system report
• "Recent activity" - What happened today

💬 **Messaging**
• "Send WhatsApp to [name] saying [message]"
• "List contacts"

📋 **Tasks & Bills**
• "Show pending tasks"
• "Upcoming bills"

🧠 **Context & Memory**
• "What do you know?" - See my knowledge
• "Who am I?" - Your profile
• "What did we do?" - Recent history

Just type naturally - I'll figure out what you need!"""
    
    # 11. Fallback - use LLM with Galidima persona
    else:
        reasoning_log.append("🤷 No specific pattern matched")
        reasoning_log.append("🤖 Routing to Galidima (Manager) via LLM")
        
        try:
            from core.llm import chat_with_agent
            
            # Build context for Galidima
            manager_context = {
                "contacts": context.get("contacts", []),
                "user": context.get("user", ""),
            }
            
            response_text = chat_with_agent(
                agent_id="manager",
                message=user_message,
                context=manager_context,
                conversation_history=conversation_history
            )
            reasoning_log.append("✅ Galidima responded via LLM")
        except Exception as e:
            reasoning_log.append(f"❌ LLM fallback error: {str(e)}")
            response_text = f"🏠 I'm Galidima, your home manager. I had trouble processing that. Try asking about status, tasks, or bills, or @mention a specific agent like @Mamadou for finance."
    
    reasoning_log.append(f"✅ Response generated ({len(response_text)} chars)")
    
    return {
        "response": response_text,
        "actions_taken": actions_taken if actions_taken else None,
        "reasoning_log": reasoning_log
    }


def _format_quick_status(status: Dict) -> str:
    """Format quick status for chat display"""
    facts = status.get("facts", {})
    alerts = facts.get("alerts", [])
    tasks = facts.get("tasks", {})
    
    text = "📊 **Quick Status**\n\n"
    
    # Alerts
    if alerts:
        text += "⚠️ **Alerts:**\n"
        for alert in alerts[:3]:
            text += f"• {alert}\n"
        text += "\n"
    
    # Tasks
    text += f"📋 **Tasks:** {tasks.get('pending', 0)} pending, {tasks.get('overdue', 0)} overdue\n\n"
    
    # Recent changes
    changes = facts.get("recent_changes", [])
    if changes:
        text += "🕐 **Recent:**\n"
        for change in changes[:3]:
            text += f"• {change}\n"
    
    # Unknowns
    unknowns = status.get("unknowns", [])
    if unknowns:
        text += "\n❓ **Unknowns:**\n"
        for u in unknowns[:2]:
            text += f"• {u}\n"
    
    return text


def _format_full_report(report: Dict) -> str:
    """Format full report for chat display"""
    text = "📊 **Full System Report**\n\n"
    
    # Agent status
    agents = report.get("agents", {})
    if agents:
        text += "🤖 **Agents:**\n"
        for name, info in list(agents.items())[:5]:
            state = info.get("state", "unknown")
            text += f"• {name}: {state}\n"
        text += "\n"
    
    # Tasks
    tasks = report.get("tasks", {})
    text += f"📋 **Tasks:** {tasks.get('running', 0)} running, {tasks.get('queued', 0)} queued\n\n"
    
    # Recommendations
    recs = report.get("recommendations", [])
    if recs:
        text += "💡 **Recommendations:**\n"
        for rec in recs[:3]:
            text += f"• {rec}\n"
    
    return text


# ============ ROUTES ============

@router.get("/history")
async def get_chat_history(conversation_id: Optional[str] = None) -> ConversationHistory:
    """
    Get conversation history.
    """
    conv_id = conversation_id or _default_conversation_id
    messages = _get_conversation(conv_id)
    
    return ConversationHistory(
        conversation_id=conv_id,
        messages=[ChatMessage(**m) for m in messages]
    )


@router.post("/send")
async def send_chat_message(request: SendMessageRequest) -> SendMessageResponse:
    """
    Send a message to the Manager and get a response.
    
    This is the main chat endpoint.
    """
    conversation_id = request.conversation_id or _default_conversation_id
    
    # Add user message to history
    _add_message(conversation_id, "user", request.message)
    
    # Get conversation history for context
    history = _get_conversation(conversation_id)
    
    # Process with Manager
    result = _process_with_manager(request.message, history)
    
    # Add assistant response to history
    msg_id = _add_message(conversation_id, "assistant", result["response"])
    
    # Record to SecondBrain (async, non-blocking)
        try:
            from api.main import get_manager
            manager = get_manager()
            manager.record_event_to_sb(
                event=f"Chat: {request.message[:50]}...",
                details=f"User: {request.message}\n\nManager: {result['response'][:200]}..."
            )
        except Exception:
            pass  # Don't fail chat if SecondBrain write fails
    
    return SendMessageResponse(
        response=result["response"],
        message_id=msg_id,
        conversation_id=conversation_id,
        actions_taken=result.get("actions_taken"),
        reasoning_log=result.get("reasoning_log")
    )


@router.post("/clear")
async def clear_chat_history(conversation_id: Optional[str] = None):
    """
    Clear conversation history.
    """
    conv_id = conversation_id or _default_conversation_id
    if conv_id in _conversations:
        _conversations[conv_id] = []
    
    return {"success": True, "cleared": conv_id}


# ============ CONVERSATION BRANCHING (LobeHub-inspired) ============

class ForkConversationRequest(BaseModel):
    """Request to fork a conversation from a specific point"""
    source_conversation_id: str = Field(..., description="Original conversation ID")
    from_message_id: str = Field(..., description="Message ID to fork from")
    new_conversation_name: Optional[str] = Field(default=None, description="Name for the new branch")


class ForkConversationResponse(BaseModel):
    """Response after forking a conversation"""
    new_conversation_id: str
    forked_from: str
    from_message_id: str
    message_count: int


# Track branching relationships
_conversation_branches: Dict[str, Dict[str, Any]] = {}  # conv_id -> {parent, from_msg, created_at}


@router.post("/fork")
async def fork_conversation(request: ForkConversationRequest) -> ForkConversationResponse:
    """
    Fork a conversation from a specific message.
    
    This creates a new conversation branch that contains all messages
    up to and including the specified message, allowing you to explore
    different paths from that point.
    
    LobeHub-inspired feature for conversation exploration.
    """
    source_conv_id = request.source_conversation_id
    from_msg_id = request.from_message_id
    
    # Validate source conversation exists
    if source_conv_id not in _conversations:
        raise HTTPException(status_code=404, detail=f"Conversation not found: {source_conv_id}")
    
    source_messages = _conversations[source_conv_id]
    
    # Find the message to fork from
    fork_index = None
    for i, msg in enumerate(source_messages):
        if msg["id"] == from_msg_id:
            fork_index = i
            break
    
    if fork_index is None:
        raise HTTPException(status_code=404, detail=f"Message not found: {from_msg_id}")
    
    # Create new conversation with messages up to fork point
    new_conv_id = request.new_conversation_name or f"{source_conv_id}_branch_{str(uuid.uuid4())[:6]}"
    
    # Check for name collision
    if new_conv_id in _conversations:
        new_conv_id = f"{new_conv_id}_{str(uuid.uuid4())[:4]}"
    
    # Copy messages up to and including fork point
    forked_messages = [msg.copy() for msg in source_messages[:fork_index + 1]]
    _conversations[new_conv_id] = forked_messages
    
    # Track branching relationship
    _conversation_branches[new_conv_id] = {
        "parent": source_conv_id,
        "from_message_id": from_msg_id,
        "created_at": datetime.now().isoformat()
    }
    
    return ForkConversationResponse(
        new_conversation_id=new_conv_id,
        forked_from=source_conv_id,
        from_message_id=from_msg_id,
        message_count=len(forked_messages)
    )


@router.get("/branches/{conversation_id}")
async def get_conversation_branches(conversation_id: str):
    """
    Get all branches (forks) of a conversation.
    
    Returns both child branches (forks from this conversation)
    and the parent branch (if this is a fork itself).
    """
    # Find children (conversations forked from this one)
    children = [
        {
            "conversation_id": child_id,
            "from_message_id": info["from_message_id"],
            "created_at": info["created_at"]
        }
        for child_id, info in _conversation_branches.items()
        if info["parent"] == conversation_id
    ]
    
    # Get parent info if this is a fork
    parent_info = _conversation_branches.get(conversation_id)
    
    return {
        "conversation_id": conversation_id,
        "parent": parent_info,
        "children": children,
        "total_branches": len(children)
    }


@router.get("/compare")
async def compare_conversations(
    conversation_a: str,
    conversation_b: str,
    from_message_id: Optional[str] = None
):
    """
    Compare two conversation branches.
    
    Useful for seeing how different paths diverged from a common point.
    Returns messages that differ between the two conversations.
    """
    if conversation_a not in _conversations:
        raise HTTPException(status_code=404, detail=f"Conversation not found: {conversation_a}")
    if conversation_b not in _conversations:
        raise HTTPException(status_code=404, detail=f"Conversation not found: {conversation_b}")
    
    msgs_a = _conversations[conversation_a]
    msgs_b = _conversations[conversation_b]
    
    # Find divergence point
    divergence_index = 0
    for i, (a, b) in enumerate(zip(msgs_a, msgs_b)):
        if a["id"] != b["id"]:
            divergence_index = i
            break
        divergence_index = i + 1
    
    return {
        "conversation_a": conversation_a,
        "conversation_b": conversation_b,
        "common_messages": divergence_index,
        "diverged_at_index": divergence_index,
        "branch_a_after_divergence": [
            {"id": m["id"], "role": m["role"], "preview": m["content"][:100]}
            for m in msgs_a[divergence_index:]
        ],
        "branch_b_after_divergence": [
            {"id": m["id"], "role": m["role"], "preview": m["content"][:100]}
            for m in msgs_b[divergence_index:]
        ]
    }


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """
    Delete a conversation (branch).
    
    Note: This does not delete child branches, only the specified conversation.
    """
    if conversation_id not in _conversations:
        raise HTTPException(status_code=404, detail=f"Conversation not found: {conversation_id}")
    
    # Remove from conversations
    del _conversations[conversation_id]
    
    # Remove branch tracking info
    if conversation_id in _conversation_branches:
        del _conversation_branches[conversation_id]
    
    # Try to delete the SecondBrain file
    try:
        vault_path = VAULT_PATH / "conversations"
        conv_file = vault_path / f"conv_{conversation_id}.md"
        if conv_file.exists():
            conv_file.unlink()
    except Exception:
        pass  # Non-blocking
    
    return {
        "success": True,
        "deleted": conversation_id,
        "message": f"Conversation {conversation_id} deleted"
    }


@router.get("/conversations")
async def list_conversations():
    """
    List all conversations.
    Returns basic info for each conversation.
    """
    _load_conversations_from_secondbrain()
    
    conversations = []
    for conv_id, messages in _conversations.items():
        branch_info = _conversation_branches.get(conv_id)
        last_msg = messages[-1] if messages else None
        
        conversations.append({
            "id": conv_id,
            "message_count": len(messages),
            "last_message_preview": last_msg["content"][:100] if last_msg else None,
            "last_message_time": last_msg["timestamp"] if last_msg else None,
            "is_branch": branch_info is not None,
            "parent_id": branch_info["parent"] if branch_info else None,
        })
    
    # Sort by last message time (most recent first)
    conversations.sort(
        key=lambda x: x["last_message_time"] or "",
        reverse=True
    )
    
    return {
        "conversations": conversations,
        "total": len(conversations)
    }
