def calculator(operation: str, a: float, b: float) -> float:
    """
    Performs basic math operations.

    Args:
        operation: The math operation to perform (add, subtract, multiply, divide)
        a: First number
        b: Second number

    Returns:
        The result of the operation
    """

    print(f"[TOOL CALLED] calculator({operation}, {a}, {b})")

    if operation == "add":
        return a + b
    elif operation == "subtract":
        return a - b
    elif operation == "multiply":
        return a * b
    elif operation == "divide":
        if b == 0:
            raise ValueError("Cannot divide by zero.")
        return a / b
    else:
        raise ValueError(f"Unknown operation: {operation}")
    
def search_court_opinions(query: str, limit: int = 5) -> dict:
    """
    Searches for court case opinions by keyword.

    Args:
        query: Search terms(e.g., "first amendment")
        limit: Maximum number of results to retur (default 5)

    Returns:
        Search results including case names, courts, and dates
    """

    import requests
    from config import COURTLISTENER_API_TOKEN
    print(f"[TOOL CALLED] search_court_opinions(query='{query}', limit={limit})")

    headers = {
        "Authorization": f"Token {COURTLISTENER_API_TOKEN}"
    }

    params ={
        "q": query,
        "type": "o", # 'o' for opinions
        "order_by": "score desc",
        "page_size": limit
    }

    response = requests.get(
        "https://www.courtlistener.com/api/rest/v4/search/",
        headers=headers,
        params=params
    )

    response.raise_for_status()
    return response.json()

def search_adelante_knowledge(query: str) -> str:
    """
    Search the Adelante Story Foundation knowledge base for information about the organization, 
    including their mission, programs (especially mortgage/housing programs), services, history, 
    and impact. Use this tool for ANY question about Adelante Story Foundation.

    Args:
        query: What to search for (e.g., "mission", "programs")

    Returns:
        Relevant information from the website
    """
    from lc_rag import search_knowledge_base

    print(f"[TOOL CALLED] search_adelante_knowledge(query='{query}')")

    result = search_knowledge_base(query, top_k=4)
    return result

async def get_rentcast_mcp_tool():
    """
    Get the Rentcast MCP tool for real estate and property data.

    This tool connects to the Rentcast MCP server and provides access to
    real estat market data, property information, and rental statistics.

    Returns:
        MCPStreamableHTTPTool Connected MCP tool instance
    """
    from agent_framework import MCPStreamableHTTPTool

    print("[TOOL LOADING] Initializing Rentcast MCP tool...")

    mcp_tool = MCPStreamableHTTPTool(
        name="rentcast",
        url="https://developers.rentcast.io/mcp",
        description="Real estate and property data from Rentcast",
        headers={"x-api-key": "96693f2137ad4e7892499c314463820d"},
        load_tools=True,
        load_prompts=False
    )

    # Await connection
    await mcp_tool.connect()

    print("[TOOL LOADED] Rentcast MCP tool ready")

    return mcp_tool
    

