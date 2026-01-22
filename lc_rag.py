#lc_rag.py - LangChain version
from langchain_community.document_loaders import WebBaseLoader, TextLoader, PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_openai import AzureOpenAIEmbeddings
from config import AZURE_OPENAI_EMBEDDINGS_ENDPOINT, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT, AZURE_OPENAI_EMBEDDINGS_API_KEY
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
    separators=["\n\n", "\n", ". "," ", ""]
)

VECTOR_STORE_PATH = "knowledge_base_faiss"

def build_knowledge_base(url: str):
    """
    Scrape a url, chunk it, embed it and save it
    
    Args:
        url: Website URL to process
    """
    print(f"scraping {url}")

    # WebBaseLoader handles the scraping automatically
    loader = WebBaseLoader(url)
    documents = loader.load()

    chunks = text_splitter.split_documents(documents)
    print(f"Created {len(chunks)} chunks")

    vectorstore = FAISS.from_documents(chunks, embeddings)
    vectorstore.save_local(VECTOR_STORE_PATH)

    print(f"Saved knowledge base to {VECTOR_STORE_PATH}")
    print("Done!")

def add_document_to_knowledge_base(file_path: str, source_name: str):
    """
    Add a text file to the existing knowledge base

    Args:
        file_path: Path to text file
        source_name: Name/label for this source
    """
    loader = TextLoader(file_path, encoding='utf-8')
    documents = loader.load()

    for doc in documents:
        doc.metadata['source'] = source_name
        doc.metadata['type'] = 'document'

    chunks = text_splitter.split_documents(documents)
    print(f"Created {len(chunks)} chunks from {file_path}")

    if os.path.exists(VECTOR_STORE_PATH):
        vectorstore = FAISS.load_local(
            VECTOR_STORE_PATH,
            embeddings,
            allow_dangerous_deserialization=True
        )
        vectorstore.add_documents(chunks)
        print(f"Added {len(chunks)} chunks to existing knowledge base")
    else:
        vectorstore = FAISS.from_documents(chunks, embeddings)
        print(f"Created new knowledge base with {len(chunks)} chunks")

    vectorstore.save_local(VECTOR_STORE_PATH)
    print("Saved!")

def add_pdf_to_knowledge_base(file_path: str, source_name: str):
    """
    Add a PDF file to the existing knowledge base

    Args:
        file_path: Path to PDF file
        source_name: Name/label for this source (e.g., 'Loan Originator Overview')
    """
    # PyPDFLoader loads PDF page-by-page
    # Each page becomes a separate Document object with page number metadata
    loader = PyPDFLoader(file_path)
    documents = loader.load()

    print(f"Loaded {len(documents)} pages from {file_path}")

    # Add custom metadata to each page/document
    for doc in documents:
        doc.metadata['source'] = source_name
        doc.metadata['type'] = 'pdf'
        # PyPDFLoader already adds 'page' metadata automatically

    # Split each page into smaller chunks based on your text_splitter config
    # This is where the magic happens - takes long pages and breaks them into
    # optimal-sized pieces for embedding
    chunks = text_splitter.split_documents(documents)
    print(f"Created {len(chunks)} chunks from {len(documents)} pages")

    # Load existing vectorstore or create new one
    if os.path.exists(VECTOR_STORE_PATH):
        vectorstore = FAISS.load_local(
            VECTOR_STORE_PATH,
            embeddings,
            allow_dangerous_deserialization=True
        )
        vectorstore.add_documents(chunks)
        print(f"Added {len(chunks)} chunks to existing knowledge base")
    else:
        vectorstore = FAISS.from_documents(chunks, embeddings)
        print(f"Created new knowledge base with {len(chunks)} chunks")

    vectorstore.save_local(VECTOR_STORE_PATH)
    print("Saved!")

def search_knowledge_base(query: str, top_k: int = 7) -> str:
    """
    Search the knowledge base for relevant chunks

    Args: 
        query: User's question
        top_k: How many results to return

    Returns:
        Combined text from top matching chunks
    """
    vectorstore = FAISS.load_local(
        VECTOR_STORE_PATH,
        embeddings,
        allow_dangerous_deserialization=True
    )

    results_with_scores = vectorstore.similarity_search_with_score(query, k=top_k)

    print(f"\n[RAG SEARCH]")
    print(f"Query: {query}")
    print(f"Top {top_k} results (scores):")
    for i, (doc, score) in enumerate(results_with_scores):
        source = doc.metadata.get('source', doc.metadata.get('url', 'uknown'))
        similarity = 1 / (1 + score)
        print(f"  {i+1}. Score: {similarity: .4f} | Source: {source}")
        print(f"      Preview: {doc.page_content[:100]}...")
    print(f"[END RAG SEARCH]\n")

    docs = [doc for doc, score in results_with_scores]
    return '\n\n'.join([doc.page_content for doc in docs])

if __name__ =="__main__":
    # Example usage - uncomment the one you want to run
    #build_knowledge_base("https://adelantestory.com")  # One time build
    #add_document_to_knowledge_base('docs/programs.txt', 'mortgage programs')
    add_pdf_to_knowledge_base('docs/Loan-Originator-Overview.pdf', 'Loan Originator Overview')
