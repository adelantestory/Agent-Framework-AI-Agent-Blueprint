# lc_rag_qdrant.py - Updated RAG with Qdrant support
"""
RAG module supporting both FAISS (local) and Qdrant (cloud/production)
Automatically uses Qdrant if credentials are available, falls back to FAISS
"""

from langchain_community.document_loaders import WebBaseLoader, TextLoader, PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
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

# Initialize embeddings (reused across functions)
embeddings = AzureOpenAIEmbeddings(
    model=AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT,
    azure_endpoint=AZURE_OPENAI_EMBEDDINGS_ENDPOINT,
    api_key=AZURE_OPENAI_EMBEDDINGS_API_KEY,
    api_version="2024-02-01"
)

# Text splitter configuration
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=800,
    chunk_overlap=100,
    separators=["\n\n", "\n", ". ", " ", ""]
)

# Determine which vector store to use
USE_QDRANT = bool(QDRANT_URL and QDRANT_API_KEY)
FAISS_PATH = "knowledge_base_faiss"

if USE_QDRANT:
    print(f"[RAG] Using Qdrant vector database at {QDRANT_URL}")
else:
    print(f"[RAG] Using local FAISS vector database (set QDRANT_URL and QDRANT_API_KEY to use Qdrant)")


def get_qdrant_client():
    """Get initialized Qdrant client"""
    if not USE_QDRANT:
        raise ValueError("Qdrant credentials not configured. Set QDRANT_URL and QDRANT_API_KEY in .env")

    return QdrantClient(
        url=QDRANT_URL,
        api_key=QDRANT_API_KEY
    )


def get_vectorstore():
    """
    Get the appropriate vector store (Qdrant or FAISS)
    Returns the configured vector store instance
    """
    if USE_QDRANT:
        client = get_qdrant_client()
        return Qdrant(
            client=client,
            collection_name=QDRANT_COLLECTION_NAME,
            embeddings=embeddings
        )
    else:
        if not os.path.exists(FAISS_PATH):
            raise FileNotFoundError(
                f"FAISS knowledge base not found at {FAISS_PATH}. "
                "Run build_knowledge_base() first or configure Qdrant."
            )
        return FAISS.load_local(FAISS_PATH, embeddings, allow_dangerous_deserialization=True)


def build_knowledge_base(url: str):
    """
    Scrape a URL, chunk it, embed it and save to vector store

    Args:
        url: Website URL to process
    """
    print(f"Scraping {url}...")

    # Load and process documents
    loader = WebBaseLoader(url)
    documents = loader.load()

    chunks = text_splitter.split_documents(documents)
    print(f"Created {len(chunks)} chunks")

    if USE_QDRANT:
        # Store in Qdrant
        print("Uploading to Qdrant...")

        # Check if collection exists
        client = get_qdrant_client()
        collections = client.get_collections().collections
        collection_names = [c.name for c in collections]

        if QDRANT_COLLECTION_NAME not in collection_names:
            print(f"Creating collection: {QDRANT_COLLECTION_NAME}")
            sample_embedding = embeddings.embed_query("test")
            vector_size = len(sample_embedding)

            client.create_collection(
                collection_name=QDRANT_COLLECTION_NAME,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE)
            )

        Qdrant.from_documents(
            documents=chunks,
            embedding=embeddings,
            url=QDRANT_URL,
            api_key=QDRANT_API_KEY,
            collection_name=QDRANT_COLLECTION_NAME,
            force_recreate=False
        )
        print(f"✅ Saved to Qdrant collection: {QDRANT_COLLECTION_NAME}")
    else:
        # Store in FAISS
        vectorstore = FAISS.from_documents(chunks, embeddings)
        vectorstore.save_local(FAISS_PATH)
        print(f"✅ Saved to local FAISS at {FAISS_PATH}")

    print("Done!")


def add_document_to_knowledge_base(file_path: str, source_name: str):
    """
    Add a document file to the existing knowledge base

    Args:
        file_path: Path to the file (txt, pdf)
        source_name: Name to identify this source
    """
    print(f"Loading document from {file_path}...")

    # Determine loader based on file extension
    if file_path.endswith('.pdf'):
        loader = PyPDFLoader(file_path)
    else:
        loader = TextLoader(file_path)

    documents = loader.load()

    # Add source metadata
    for doc in documents:
        doc.metadata['source'] = source_name

    chunks = text_splitter.split_documents(documents)
    print(f"Created {len(chunks)} chunks from {source_name}")

    if USE_QDRANT:
        # Add to Qdrant
        print("Adding to Qdrant...")
        Qdrant.from_documents(
            documents=chunks,
            embedding=embeddings,
            url=QDRANT_URL,
            api_key=QDRANT_API_KEY,
            collection_name=QDRANT_COLLECTION_NAME,
            force_recreate=False
        )
        print(f"✅ Added to Qdrant collection: {QDRANT_COLLECTION_NAME}")
    else:
        # Add to FAISS
        existing_store = FAISS.load_local(FAISS_PATH, embeddings, allow_dangerous_deserialization=True)
        new_store = FAISS.from_documents(chunks, embeddings)
        existing_store.merge_from(new_store)
        existing_store.save_local(FAISS_PATH)
        print(f"✅ Added to local FAISS at {FAISS_PATH}")

    print("Done!")


def search_knowledge_base(query: str, k: int = 3):
    """
    Search the knowledge base for relevant documents

    Args:
        query: Search query
        k: Number of results to return

    Returns:
        Combined text from top matching chunks (as string)
    """
    if USE_QDRANT:
        # Use Qdrant client directly (more reliable than LangChain wrapper)
        client = get_qdrant_client()

        # Get query embedding
        query_vector = embeddings.embed_query(query)

        # Search Qdrant
        search_results = client.query_points(
            collection_name=QDRANT_COLLECTION_NAME,
            query=query_vector,
            limit=k
        )

        print(f"\n[RAG SEARCH - Qdrant]")
        print(f"Query: {query}")
        print(f"Top {k} results:")

        results_text = []
        for i, point in enumerate(search_results.points, 1):
            content = point.payload.get('page_content', '')
            source = point.payload.get('metadata', {}).get('source', 'unknown')
            print(f"  {i}. Score: {point.score:.4f} | Source: {source}")
            print(f"     Preview: {content[:100]}...")
            results_text.append(content)

        print(f"[END RAG SEARCH]\n")

        # Return combined text like the old FAISS version
        return '\n\n'.join(results_text)
    else:
        # Use FAISS
        vectorstore = get_vectorstore()
        results = vectorstore.similarity_search(query, k=k)

        print(f"\n[RAG SEARCH - FAISS]")
        print(f"Query: {query}")
        print(f"Top {k} results:")
        for i, doc in enumerate(results, 1):
            source = doc.metadata.get('source', 'unknown')
            print(f"  {i}. Source: {source}")
            print(f"     Preview: {doc.page_content[:100]}...")
        print(f"[END RAG SEARCH]\n")

        # Return combined text
        return '\n\n'.join([doc.page_content for doc in results])


def get_retriever(k: int = 3):
    """
    Get a retriever for the knowledge base
    Used by LangChain chains

    Args:
        k: Number of documents to retrieve

    Returns:
        LangChain retriever
    """
    vectorstore = get_vectorstore()
    return vectorstore.as_retriever(search_kwargs={"k": k})


if __name__ == "__main__":
    # Example usage
    print("\nVector Store Info:")
    print(f"  Using: {'Qdrant' if USE_QDRANT else 'FAISS (local)'}")
    if USE_QDRANT:
        print(f"  URL: {QDRANT_URL}")
        print(f"  Collection: {QDRANT_COLLECTION_NAME}")
    else:
        print(f"  Path: {FAISS_PATH}")

    # Test search
    try:
        print("\nTesting search...")
        results = search_knowledge_base("What programs does Adelante offer?")
        print(f"✅ Found {len(results)} results")
        print(f"\nFirst result preview:")
        print(results[0].page_content[:200] + "...")
    except Exception as e:
        print(f"❌ Error: {e}")
