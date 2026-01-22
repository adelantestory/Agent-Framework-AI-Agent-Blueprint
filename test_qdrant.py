"""Simple test to verify Qdrant is working"""
from qdrant_client import QdrantClient
from langchain_openai import AzureOpenAIEmbeddings
from config import (
    QDRANT_URL,
    QDRANT_API_KEY,
    QDRANT_COLLECTION_NAME,
    AZURE_OPENAI_EMBEDDINGS_ENDPOINT,
    AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT,
    AZURE_OPENAI_EMBEDDINGS_API_KEY
)

# Initialize
print("Connecting to Qdrant...")
client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

print(f"Collection: {QDRANT_COLLECTION_NAME}")
collection_info = client.get_collection(QDRANT_COLLECTION_NAME)
print(f"Total points: {collection_info.points_count}")

# Test search
print("\nTesting search...")
embeddings = AzureOpenAIEmbeddings(
    model=AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT,
    azure_endpoint=AZURE_OPENAI_EMBEDDINGS_ENDPOINT,
    api_key=AZURE_OPENAI_EMBEDDINGS_API_KEY,
    api_version="2024-02-01"
)

query = "What programs does Adelante offer?"
print(f"Query: {query}")

query_vector = embeddings.embed_query(query)
print(f"Query vector size: {len(query_vector)}")

results = client.query_points(
    collection_name=QDRANT_COLLECTION_NAME,
    query=query_vector,
    limit=3
)

print(f"\nFound {len(results.points)} results:")
for i, point in enumerate(results.points, 1):
    print(f"\n--- Result {i} (score: {point.score:.4f}) ---")
    content = point.payload.get('page_content', '')[:200]
    print(f"Content: {content}...")
    print(f"Source: {point.payload.get('metadata', {}).get('source', 'N/A')}")

print("\nQdrant is working correctly!")
