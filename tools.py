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
    Search the Adelante Story Foundation knowledge base (now in Qdrant) for information about the organization,
    including their mission, programs (especially mortgage/housing programs), home lending laws, regulations and governing bodies, services, history,
    and impact. Use this tool for ANY question about Adelante Story Foundation.

    Args:
        query: What to search for (e.g., "mission", "programs", "housing assistance", "home lending)

    Returns:
        Relevant information from the website
    """
    from lc_rag_qdrant import search_knowledge_base

    print(f"[TOOL CALLED] search_adelante_knowledge(query='{query}') - Using Qdrant")

    result = search_knowledge_base(query, k=7)
    return result

def search_home_listings(city: str = None, state: str = None, zip_code: str = None,
                        min_price: float = None, max_price: float = None) -> dict:
    """
    Search for active homes for sale using the RentCast API.

    Use this tool when users ask about homes for sale, real estate listings, or properties
    available in a specific location. Return as many listings as are available.

    Args:
        city: City name (e.g., "Scottsdale")
        state: Two-letter state code (e.g., "AZ")
        zip_code: 5-digit ZIP code (e.g., "85254")
        min_price: Minimum listing price in dollars (optional)
        max_price: Maximum listing price in dollars (optional)

    Returns:
        Dictionary containinghome sale listings with details like
        address, price, bedrooms, bathrooms, square footage, etc.
    """
    import requests
    from config import RENTCAST_API_KEY

    print(f"[TOOL CALLED] search_home_listings(city='{city}', state='{state}', zip_code='{zip_code}', "
          f"min_price={min_price}, max_price={max_price})")

    if not RENTCAST_API_KEY:
        raise ValueError("RENTCAST_API_KEY not found in environment variables")

    # Build API parameters
    params = {
        "status": "Active"
    }

    if city:
        params["city"] = city
    if state:
        params["state"] = state
    if zip_code:
        params["zipCode"] = zip_code
    if min_price is not None:
        params["minPrice"] = min_price
    if max_price is not None:
        params["maxPrice"] = max_price

    headers = {
        "accept": "application/json",
        "X-Api-Key": RENTCAST_API_KEY
    }

    try:
        response = requests.get(
            "https://api.rentcast.io/v1/listings/sale",
            headers=headers,
            params=params
        )
        response.raise_for_status()
        return response.json()

    except requests.exceptions.HTTPError as e:
        error_msg = f"RentCast API error: {e.response.status_code}"
        if e.response.text:
            error_msg += f" - {e.response.text}"
        raise Exception(error_msg)
    except Exception as e:
        raise Exception(f"Error fetching home listings: {str(e)}")

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

def tavily_search(query: str, max_results: int = 5) -> dict:
    """
    Search the web using Tavily API.

    Use this when users ask questions requiring current information,
    recent news, or real-time data not in your knowledge base.
    """
    from tavily import TavilyClient
    from config import TAVILY_API_KEY

    print(f"[TOOL] 🔍 Tavily search: '{query}' (max {max_results} results)")

    if not TAVILY_API_KEY:
        raise ValueError("TAVILY_API_KEY not found")
    
    client = TavilyClient(api_key=TAVILY_API_KEY)
    response = client.search(query=query, max_results=max_results)
    return response
    

