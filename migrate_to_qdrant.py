"""
Migration script to move FAISS knowledge base to Qdrant
Run this once after setting up Qdrant from Azure Marketplace
"""

from langchain_community.vectorstores import FAISS
from langchain_qdrant import Qdrant
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from langchain_openai import AzureOpenAIEmbeddings
from config import (
    AZURE_OPENAI_EMBEDDINGS_ENDPOINT,
    AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT,
    AZURE_OPENAI_EMBEDDINGS_API_KEY,
    QDRANT_URL,
    QDRANT_API_KEY,
    QDRANT_COLLECTION_NAME
)
import os

def migrate_faiss_to_qdrant():
    """
    Migrate existing FAISS knowledge base to Qdrant
    """
    print("Starting migration from FAISS to Qdrant...")

    # Check if Qdrant credentials are set
    if not QDRANT_URL or not QDRANT_API_KEY:
        print("❌ Error: QDRANT_URL and QDRANT_API_KEY must be set in .env file")
        print("   Get these from Azure Portal after purchasing Qdrant from Marketplace")
        return

    # Initialize embeddings
    print("Initializing Azure OpenAI embeddings...")
    embeddings = AzureOpenAIEmbeddings(
        model=AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT,
        azure_endpoint=AZURE_OPENAI_EMBEDDINGS_ENDPOINT,
        api_key=AZURE_OPENAI_EMBEDDINGS_API_KEY,
        api_version="2024-02-01"
    )

    # Load existing FAISS knowledge base
    faiss_path = "knowledge_base_faiss"
    if not os.path.exists(faiss_path):
        print(f"❌ Error: FAISS knowledge base not found at {faiss_path}")
        print("   Run build_knowledge_base() first to create the knowledge base")
        return

    print(f"Loading FAISS knowledge base from {faiss_path}...")
    faiss_store = FAISS.load_local(faiss_path, embeddings, allow_dangerous_deserialization=True)

    # Get all documents from FAISS
    print("Extracting documents from FAISS...")
    # FAISS doesn't have a direct way to get all documents, so we'll use docstore
    all_docs = []
    for doc_id in faiss_store.docstore._dict.keys():
        doc = faiss_store.docstore._dict[doc_id]
        all_docs.append(doc)

    print(f"Found {len(all_docs)} documents to migrate")

    # Initialize Qdrant client
    print(f"Connecting to Qdrant at {QDRANT_URL}...")
    qdrant_client = QdrantClient(
        url=QDRANT_URL,
        api_key=QDRANT_API_KEY
    )

    # Check if collection exists, if not create it
    collections = qdrant_client.get_collections().collections
    collection_names = [c.name for c in collections]

    if QDRANT_COLLECTION_NAME not in collection_names:
        print(f"Creating new collection: {QDRANT_COLLECTION_NAME}")
        # Get embedding dimension from the first document
        sample_embedding = embeddings.embed_query("test")
        vector_size = len(sample_embedding)

        qdrant_client.create_collection(
            collection_name=QDRANT_COLLECTION_NAME,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE)
        )
    else:
        print(f"Collection {QDRANT_COLLECTION_NAME} already exists")

    # Migrate documents to Qdrant
    print("Uploading documents to Qdrant...")
    qdrant_store = Qdrant.from_documents(
        documents=all_docs,
        embedding=embeddings,
        url=QDRANT_URL,
        api_key=QDRANT_API_KEY,
        collection_name=QDRANT_COLLECTION_NAME,
        force_recreate=False  # Don't recreate if collection exists
    )

    print("✅ Migration complete!")
    print(f"   - Migrated {len(all_docs)} documents")
    print(f"   - Collection: {QDRANT_COLLECTION_NAME}")
    print(f"   - Qdrant URL: {QDRANT_URL}")
    print("\nNext steps:")
    print("1. Test the Qdrant integration by running the search")
    print("2. Once verified, you can delete the local FAISS files")
    print("3. Update your code to use Qdrant by default")

def test_qdrant_search(query: str = "What programs does Adelante offer?"):
    """
    Test the Qdrant integration with a sample search
    """
    print(f"\nTesting Qdrant search with query: '{query}'")

    if not QDRANT_URL or not QDRANT_API_KEY:
        print("❌ Error: QDRANT_URL and QDRANT_API_KEY must be set")
        return

    # Initialize embeddings
    embeddings = AzureOpenAIEmbeddings(
        model=AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT,
        azure_endpoint=AZURE_OPENAI_EMBEDDINGS_ENDPOINT,
        api_key=AZURE_OPENAI_EMBEDDINGS_API_KEY,
        api_version="2024-02-01"
    )

    # Connect to Qdrant
    qdrant_client = QdrantClient(
        url=QDRANT_URL,
        api_key=QDRANT_API_KEY
    )

    qdrant_store = Qdrant(
        client=qdrant_client,
        collection_name=QDRANT_COLLECTION_NAME,
        embeddings=embeddings
    )

    # Perform search
    print("Searching...")
    results = qdrant_store.similarity_search(query, k=3)

    print(f"\n✅ Found {len(results)} results:")
    for i, doc in enumerate(results, 1):
        print(f"\n--- Result {i} ---")
        print(f"Content: {doc.page_content[:200]}...")
        print(f"Source: {doc.metadata.get('source', 'N/A')}")

    print("\n✅ Qdrant is working correctly!")

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # Test mode
        query = sys.argv[2] if len(sys.argv) > 2 else "What programs does Adelante offer?"
        test_qdrant_search(query)
    else:
        # Migration mode
        migrate_faiss_to_qdrant()

        # After migration, run a test
        print("\n" + "="*50)
        response = input("\nWould you like to test the Qdrant integration now? (y/n): ")
        if response.lower() == 'y':
            test_qdrant_search()
