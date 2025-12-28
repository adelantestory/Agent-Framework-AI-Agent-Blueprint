import os
from dotenv import load_dotenv

load_dotenv()

# Azure OpenAI credentials (for the AI model)
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")

# Agent configuration
MODEL_NAME = "gpt-4o"
TEMPERATURE = 0.7
MAX_TOKENS = 1000

# CourtListener API
COURTLISTENER_API_TOKEN = os.getenv("COURTLISTENER_API_TOKEN")

# Analytics Configuration
ENABLE_CONVERSATION_LOGGING = os.getenv("ENABLE_CONVERSATION_LOGGING", "true").lower() == "true"
CONVERSATION_LOG_FILE = "logs/conversations.jsonl"

# Azure Application Insights (for OpenTelemetry observability)
APPLICATIONINSIGHTS_CONNECTION_STRING = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
ENABLE_OBSERVABILITY = os.getenv("ENABLE_OBSERVABILITY", "false").lower() == "true"




