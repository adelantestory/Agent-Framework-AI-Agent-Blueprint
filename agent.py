import asyncio
import time
import json
import os
from xmlrpc import client
from agent_framework.observability import setup_observability
from openai import base_url
from config import APPLICATIONINSIGHTS_CONNECTION_STRING, ENABLE_OBSERVABILITY, MODEL_PROVIDER
from pathlib import Path
from agent_framework.azure import AzureOpenAIChatClient
from agent_framework.openai import OpenAIChatClient
from agent_framework import AgentRunContext, FunctionInvocationContext, ChatContext
from azure.identity import AzureCliCredential
from config import AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_DEPLOYMENT, ENABLE_CONVERSATION_LOGGING, CONVERSATION_LOG_FILE, OLLAMA_ENDPOINT, OLLAMA_MODEL_NAME
from tools import calculator, search_court_opinions, search_adelante_knowledge, get_rentcast_mcp_tool, search_home_listings, tavily_search
from analytics import InMemoryAnalytics, initialize_analytics, get_analytics_backend
from datetime import datetime

# Initialize analytics backend
initialize_analytics(InMemoryAnalytics())

# Initialize OpenTelemetry observability (if enabled)
if ENABLE_OBSERVABILITY and APPLICATIONINSIGHTS_CONNECTION_STRING:
    setup_observability(
        applicationinsights_connection_string=APPLICATIONINSIGHTS_CONNECTION_STRING
    )
    print("[OBSERVABILITY] OpenTelemetry enabled - sending traces to Application Insights")
elif ENABLE_OBSERVABILITY:
    print("[OBSERVABILITY] WARNING: ENABLE_OBSERVABILITY=true but no connection string found")

# Create logs directory if conversation logging is enabled
if ENABLE_CONVERSATION_LOGGING:
    Path("logs").mkdir(exist_ok=True)


# Middleware for tracking agent runs
async def agent_middleware(context: AgentRunContext, next_handler):
    """Middleware to track agent execution"""
    backend = get_analytics_backend()

    print(f"[AGENT] 🚀 Agent started processing request")

    # Capture user prompt
    user_prompt = None
    if hasattr(context, 'messages') and context.messages:
        # Get the last user message
        for msg in reversed(context.messages):
            if hasattr(msg, 'role') and msg.role.value == 'user':
                user_prompt = getattr(msg, 'text', None)
                break

    # Track conversation start (in-memory)
    if user_prompt:
        backend.track_conversation(user_prompt=user_prompt)

    start_time = time.time()

    try:
        await next_handler(context)
        duration = (time.time() - start_time) * 1000

        # Capture agent output
        agent_output = None
        token_usage = None

        if hasattr(context, 'result') and context.result:
            agent_output = getattr(context.result, 'text', None)

            # Get token usage
            usage = getattr(context.result, 'usage_details', None)
            if usage:
                token_usage = {
                    "total": getattr(usage, 'total_token_count', 0),
                    "input": getattr(usage, 'input_token_count', 0),
                    "output": getattr(usage, 'output_token_count', 0)
                }

        # Track conversation completion (in-memory)
        if agent_output:
            backend.track_conversation(
                agent_output=agent_output,
                tokens=token_usage,
                duration_ms=duration
            )

        # Optional: Log to file
        if ENABLE_CONVERSATION_LOGGING and user_prompt and agent_output:
            _log_conversation_to_file(user_prompt, agent_output, token_usage, duration)

        print(f"[AGENT] ✅ Agent completed ({duration:.0f}ms)")
        backend.track_event("agent_end", {"duration_ms": duration})

    except Exception as e:
        print(f"[AGENT] ❌ Error in agent_middleware: {e}")
        backend.track_event("error", {"message": str(e)})
        raise


def _log_conversation_to_file(user_prompt: str, agent_output: str, tokens: dict, duration_ms: float):
    """Helper function to log conversation to JSONL file"""
    try:
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "user_prompt": user_prompt[:1000],  # Truncate if very long
            "agent_output": agent_output[:1000],
            "tokens": tokens,
            "duration_ms": duration_ms
        }

        with open(CONVERSATION_LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry) + '\n')

    except Exception as e:
        print(f"[WARN] Failed to log conversation to file: {e}")


# Middleware for tracking function/tool calls
async def function_middleware(context: FunctionInvocationContext, next_handler):
    """Middleware to track tool/function invocations"""
    backend = get_analytics_backend()

    try:
        # Get function object and extract name
        function = getattr(context, 'function', None)
        if function:
            tool_name = getattr(function, 'name', None) or getattr(function, '__name__', 'unknown')
        else:
            tool_name = 'unknown'

        tool_args = getattr(context, 'arguments', {})

        print(f"[AGENT] 🔧 Tool starting: {tool_name}")
        print(f"[AGENT]    Arguments: {tool_args}")

        backend.track_event("tool_call_start", {
            "tool_name": tool_name,
            "arguments": str(tool_args)[:200]
        })

        start_time = time.time()

        await next_handler(context)

        duration = (time.time() - start_time) * 1000
        print(f"[AGENT] ✓ Tool completed: {tool_name} ({duration:.0f}ms)")

        backend.track_event("tool_call_end", {
            "tool_name": tool_name,
            "duration_ms": duration
        })
    except Exception as e:
        # tool_name is already defined from the try block
        print(f"[AGENT] ❌ Tool error in {tool_name}: {e}")
        backend.track_event("error", {
            "message": f"Tool {tool_name} failed: {str(e)}"
        })
        raise


# Middleware for tracking LLM/chat calls
async def chat_middleware(context: ChatContext, next_handler):
    """Middleware to track LLM chat completions"""
    backend = get_analytics_backend()

    try:
        print(f"[AGENT] 🤖 LLM call started")
        backend.track_event("llm_call_start", {})

        await next_handler(context)

        # Try multiple ways to get token usage
        usage_found = False
        total = 0
        prompt = 0
        completion = 0

        # Method 1: context.result.usage_details (correct attribute name)
        if hasattr(context, 'result') and context.result:
            result = context.result
            usage = getattr(result, 'usage_details', None)
            if usage:
                # Agent Framework uses different attribute names
                total = getattr(usage, 'total_token_count', 0)
                prompt = getattr(usage, 'input_token_count', 0)
                completion = getattr(usage, 'output_token_count', 0)

                if total > 0:
                    usage_found = True

        # Method 2: context.usage
        if not usage_found and hasattr(context, 'usage'):
            usage = context.usage
            total = getattr(usage, 'total_tokens', 0)
            prompt = getattr(usage, 'prompt_tokens', 0)
            completion = getattr(usage, 'completion_tokens', 0)
            usage_found = True

        if usage_found:
            print(f"[AGENT] ✓ LLM completed")
            print(f"[AGENT]    Tokens: {total} (prompt: {prompt}, completion: {completion})")

            backend.track_event("llm_call_end", {
                "tokens_total": total,
                "tokens_prompt": prompt,
                "tokens_completion": completion
            })

            backend.track_metric("llm_call", 1)
            backend.track_metric("tokens_total", total)
            backend.track_metric("tokens_prompt", prompt)
            backend.track_metric("tokens_completion", completion)
        else:
            print(f"[AGENT] ✓ LLM completed (no usage data found)")

    except Exception as e:
        print(f"[AGENT] ❌ Error in chat_middleware: {e}")
        # Don't re-raise, let the agent continue
        pass


async def create_agent(rentcast_tool=None):
    """Create and return a simple agent"""

    # Initialize MCP tool
    if rentcast_tool is None:
        rentcast_tool = await get_rentcast_mcp_tool()

    # Initialize the appropriate client based on MODEL_PROVIDER
    if MODEL_PROVIDER == "ollama":
        # Use local Ollama model
        client = OpenAIChatClient(
            base_url=OLLAMA_ENDPOINT,
            model_id=OLLAMA_MODEL_NAME,
            api_key="not-needed"
        )
        print(f"🦙 Using Ollama model: {OLLAMA_MODEL_NAME} at {OLLAMA_ENDPOINT}")
    else:
        client = AzureOpenAIChatClient(
            endpoint=AZURE_OPENAI_ENDPOINT,
            deployment_name=AZURE_OPENAI_DEPLOYMENT,
            credential=AzureCliCredential()
        )
        print(f"☁️ Using Azure OpenAI model: {AZURE_OPENAI_DEPLOYMENT} at {AZURE_OPENAI_ENDPOINT}")
    agent = client.create_agent(
        name="TestBot",
        instructions="""You are a representative of the nonprofit organization,
        the Adelante Story Foundation. You are bilingual (English/Spanish).

        LANGUAGE: Always respond in the same language the user writes in. If the user writes
        in Spanish, answer completely in Spanish. If in English, answer in English.

        INTRODUCTION: On only the initial chat completion of the session prompt by saying "Hi I'm Addie your AI assistant from the Adelante Story Foundation.
        I can provide information about our Housing, Technical Skilling, and Community Outreach programs...and more. On further responses, do not reintroduce yourself.
        So, how can I help you today?"

        KNOWLEDGE: Start with your general housing expertise for questions, and then augment and refine your answers by searching
        the knowledge base. Reference https://adelantestory.com for background. You also have access to real estate
        and property data through Rentcast for housing-related questions.

        HOME LISTINGS - CRITICAL INSTRUCTION: 
        When a user asks about homes for sale in a specific city or ZIP code, you MUST follow this exact process:

        1. FIRST: Check if they mentioned a price range
        2. IF NO price range mentioned: STOP and ask "Would you like to specify a price range (minimum and maximum price)?" 
            - DO NOT search yet - wait for their response
        3. ONLY AFTER confirming price preferences: Use the search_home_listings tool
        4. Return up to 10 active listings

        GENERAL QUESTIONS: For general questions about current events, recent news, or real-time data not in your knowledge base.
        If one of the purpose built tools seems to lack detail augment it with a Tavily web search using the tavily_search tool.

        FORMATTING: Format your responses for readability:
        - Use line breaks between paragraphs
        - Use bullet points (-) for lists of items
        - Use numbered lists (1., 2., 3.) for sequential steps
        - Keep paragraphs concise (2-3 sentences max)
        - Use **bold** for emphasis on important terms

        Example format:
        Here's a clear introduction paragraph.

        Key points to consider:
        - First important point
        - Second important point
        - Third important point

        Additional context in a new paragraph.""",
        tools=[calculator, search_court_opinions, search_adelante_knowledge, rentcast_tool, tavily_search],
        middleware=[agent_middleware, function_middleware, chat_middleware],  # Wire up middleware for observability
    )

    return agent






