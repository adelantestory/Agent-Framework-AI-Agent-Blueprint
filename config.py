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

# RentCast API
RENTCAST_API_KEY = os.getenv("RENTCAST_API_KEY")

# Analytics Configuration
ENABLE_CONVERSATION_LOGGING = os.getenv("ENABLE_CONVERSATION_LOGGING", "true").lower() == "true"
CONVERSATION_LOG_FILE = "logs/conversations.jsonl"

# Azure Application Insights (for OpenTelemetry observability)
APPLICATIONINSIGHTS_CONNECTION_STRING = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
ENABLE_OBSERVABILITY = os.getenv("ENABLE_OBSERVABILITY", "false").lower() == "true"

# Ollama Configurations
OLLAMA_ENDPOINT = os.getenv("OLLAMA_ENDPOINT", "http://localhost:11434")
OLLAMA_MODEL_NAME = os.getenv("OLLAMA_MODEL_NAME", "llama2")

# Model Provider Selection
MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "azure_openai")  # Options: 'azure_openai', 'ollama'

# Tavily API Key
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

# Azure OpenAI Embeddings (for RAG)
AZURE_OPENAI_EMBEDDINGS_ENDPOINT = os.getenv("AZURE_OPENAI_EMBEDDINGS_ENDPOINT", AZURE_OPENAI_ENDPOINT)
AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT = os.getenv("AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT", "text-embedding-3-small")
AZURE_OPENAI_EMBEDDINGS_API_KEY = os.getenv("AZURE_OPENAI_EMBEDDINGS_API_KEY", AZURE_OPENAI_API_KEY)

# Qdrant Vector Database (purchased via Azure Marketplace)
QDRANT_URL = os.getenv("QDRANT_URL")  # e.g., https://xyz.qdrant.io:6333
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
QDRANT_COLLECTION_NAME = os.getenv("QDRANT_COLLECTION_NAME", "adelante_knowledge")



