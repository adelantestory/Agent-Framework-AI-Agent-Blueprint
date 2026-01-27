# app.py - FastAPI version with MCP connection pooling
# This is a production-ready FastAPI version with connection pooling, analytics, and monitoring, while app_flask_backup.py 
# is the original simple Flask implementation.

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from agent import create_agent
from tools import get_rentcast_mcp_tool
from analytics import get_analytics_backend
import uvicorn
import asyncio
from datetime import datetime

app = FastAPI(title="Adelante Story Chatbot")

# Enable CORS for WordPress embedding
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with ["https://adelantestory.com"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store active conversations
conversations = {}

# MCP Connection Pool Manager
class MCPConnectionPool:
    def __init__(self):
        self.mcp_tool = None
        self.connection_lock = asyncio.Lock()
        self.last_connection_time = None
        self.reconnect_threshold = 300  # Reconnect after 5 minutes

    async def get_mcp_tool(self):
        """Get MCP tool, reconnecting if necessary"""
        async with self.connection_lock:
            current_time = asyncio.get_event_loop().time()

            # Check if we need to reconnect
            should_reconnect = (
                self.mcp_tool is None or
                (self.last_connection_time and
                 current_time - self.last_connection_time > self.reconnect_threshold)
            )

            if should_reconnect:
                print("[MCP POOL] Creating new MCP connection...")
                try:
                    self.mcp_tool = await get_rentcast_mcp_tool()
                    self.last_connection_time = current_time
                    print("[MCP POOL] Connection established")
                except Exception as e:
                    print(f"[MCP POOL] Connection failed: {e}")
                    raise

            return self.mcp_tool

    async def reconnect(self):
        """Force reconnection"""
        async with self.connection_lock:
            print("[MCP POOL] Forcing reconnection...")
            self.mcp_tool = None
            return await self.get_mcp_tool()

# Global connection pool
mcp_pool = MCPConnectionPool()

@app.on_event("startup")
async def startup_event():
    """Initialize MCP connection on startup"""
    print("Initializing MCP connection pool...")
    try:
        await mcp_pool.get_mcp_tool()
        print("Startup complete - MCP connection ready")
    except Exception as e:
        print(f"Warning: MCP connection failed at startup: {e}")
        print("Will retry on first request")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    print("Shutting down...")

class ChatRequest(BaseModel):
    message: str
    session_id: str | None = "default-session"

class ChatResponse(BaseModel):
    response: str
    session_id: str

@app.get("/", response_class=HTMLResponse)
async def index():
    """Render the chat interface"""
    try:
        with open("templates/chat.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return HTMLResponse(
            content="<h1>Chat interface not found</h1><p>Please ensure templates/chat.html exists</p>",
            status_code=404
        )

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    """Render the analytics dashboard"""
    try:
        with open("templates/dashboard.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return HTMLResponse(
            content="<h1>Dashboard not found</h1><p>Please ensure templates/dashboard.html exists</p>",
            status_code=404
        )

@app.get("/adelante", response_class=HTMLResponse)
async def adelante_chat():
    """Render the Adelante-branded chat interface"""
    try:
        with open("templates/chat_adelante.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return HTMLResponse(
            content="<h1>Adelante chat interface not found</h1><p>Please ensure templates/chat_adelante.html exists</p>",
            status_code=404
        )

@app.get("/startup")
async def startup_check():
    """
    Lightweight startup probe endpoint for Container App.
    Returns immediately to signal the app has started and can accept connections.
    """
    return {"status": "ready"}

@app.get("/health")
async def health_check():
    """Health check endpoint for deployment monitoring"""
    return {
        "status": "healthy",
        "mcp_connected": mcp_pool.mcp_tool is not None
    }

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Handle chat messages from the user
    """
    if not request.message:
        raise HTTPException(status_code=400, detail="No message provided")

    # Use default session if none provided
    session_id = request.session_id or "default-session"

    # Get or create conversation
    if session_id not in conversations:
        conversations[session_id] = {'history': [], 'agent': None}

    conversation = conversations[session_id]

    try:
        # Get MCP tool from pool (reuses connection)
        mcp_tool = await mcp_pool.get_mcp_tool()

        # Create or reusse agent with pooled MCP connection
        if conversation['agent'] is None:
            print(f"[SESSION] Creating NEW agent for session {session_id}")
            conversation['agent'] = await create_agent(rentcast_tool=mcp_tool)
        else:
            print(f"[SESSION] Reusing EXISTING agent for session {session_id}")

        agent = conversation['agent']

        # Get response from agent
        result = await agent.run(request.message)
        response_text = result.text

    except Exception as e:
        print(f"[ERROR] Chat failed: {e}")

        # Try to reconnect MCP and retry once
        try:
            print("[RETRY] Attempting to reconnect MCP and retry...")
            mcp_tool = await mcp_pool.reconnect()
            agent = await create_agent(rentcast_tool=mcp_tool)
            result = await agent.run(request.message)
            response_text = result.text
            print("[RETRY] Success after reconnection")
        except Exception as retry_error:
            print(f"[RETRY] Failed: {retry_error}")
            raise HTTPException(
                status_code=500,
                detail=f"Agent error: {str(retry_error)}"
            )

    # Store in history
    conversation['history'].append({
        'user': request.message,
        'agent': response_text
    })

    return ChatResponse(
        response=response_text,
        session_id=session_id
    )

@app.get("/api/sessions")
async def list_sessions():
    """Debug endpoint to view active sessions"""
    return {
        "active_sessions": len(conversations),
        "sessions": list(conversations.keys())
    }

@app.get("/api/analytics")
async def get_analytics():
    """
    Get real-time analytics and metrics

    Returns:
        Analytics summary including:
        - Event counts
        - Tool usage statistics
        - LLM token metrics
        - Error tracking
    """
    backend = get_analytics_backend()
    if not backend:
        raise HTTPException(status_code=503, detail="Analytics backend not initialized")

    return backend.get_analytics()

@app.post("/api/analytics/export")
async def export_analytics():
    """
    Export analytics data to a JSON file

    Returns:
        Information about the exported file
    """
    backend = get_analytics_backend()
    if not backend:
        raise HTTPException(status_code=503, detail="Analytics backend not initialized")

    filename = f"analytics_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    result = backend.export_to_file(filename)

    if result:
        return {
            "status": "success",
            "filename": filename,
            "message": f"Analytics exported to {filename}"
        }
    else:
        raise HTTPException(status_code=500, detail="Failed to export analytics")

@app.get("/api/analytics/events")
async def get_recent_events(limit: int = 50):
    """
    Get recent events for debugging

    Args:
        limit: Maximum number of recent events to return (default 50)

    Returns:
        List of recent events
    """
    backend = get_analytics_backend()
    if not backend:
        raise HTTPException(status_code=503, detail="Analytics backend not initialized")

    analytics = backend.get_analytics()
    return {
        "recent_events_count": analytics.get("recent_events_count", 0),
        "note": "Full event history available in exported JSON files"
    }

@app.get("/api/analytics/conversations")
async def get_recent_conversations(limit: int = 20):
    """
    Get recent conversation turns (user prompts and agent responses)

    Args:
        limit: Maximum number of recent conversations to return (default 20, max 20)

    Returns:
        List of recent conversations with prompts, outputs, tokens, and duration
    """
    backend = get_analytics_backend()
    if not backend:
        raise HTTPException(status_code=503, detail="Analytics backend not initialized")

    # Limit to max 20 to avoid large responses
    limit = min(limit, 20)

    conversations = backend.get_recent_conversations(limit)

    return {
        "count": len(conversations),
        "conversations": conversations
    }

if __name__ == '__main__':
    uvicorn.run(
        app,
        host='0.0.0.0',
        port=5000,
        log_level="info"
    )
