from playwright.sync_api import sync_playwright
from openai import AzureOpenAI
from config import AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY
import json
import numpy as np



def scrape_page(url: str) -> dict[str, str]:
    """
   Scrape a page using Playwright (handles JavaScript)
    """
    print(f"Scraping: {url}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url)
        page.wait_for_load_state('networkidle')
        text = page.inner_text('body')
        browser.close()

    return {'url': url, 'text': text}


def chunk_text(text: str, chunk_size: int = 150) -> list[str]:
    """
    Split text into chunks of approxiamately chunk_size characters
    
    Args:
        text: The text to chunk
        chunk_size: Target size for each chunk
        
    Returns:
        List of text chunks
    """
    words = text.split()
    chunks = []
    current_chunk =[]
    current_size = 0
    
    for word in words:
        word_len = len(word) + 1 # +1 for space
        if current_size + word_len > chunk_size and current_chunk:
            chunks.append(' '.join(current_chunk))
            current_chunk = [word]
            current_size = word_len
        else:
            current_chunk.append(word)
            current_size += word_len

    if current_chunk:
        chunks.append(' '.join(current_chunk))

    return chunks

'''
def chunk_text(text: str, chunk_size: int = 150, overlap: int = 15) -> list[str]:
    """
    Split text into chunks with overlap
    
    Args:
        text: The text to chunk
        chunk_size: Target size for each chunk (default 150)
        overlap: Number of characters to overlap between chunks (default 30)
        
    Returns:
        List of text chunks with overlap
    """
    words = text.split()
    chunks = []
    start_idx = 0
    
    while start_idx < len(words):
        # Build chunk from start_idx
        current_chunk = []
        current_size = 0
        idx = start_idx
        
        # Add words until we hit chunk_size
        while idx < len(words) and current_size < chunk_size:
            word = words[idx]
            current_chunk.append(word)
            current_size += len(word) + 1  # +1 for space
            idx += 1
        
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        # Calculate how many words to step back for overlap
        overlap_chars = 0
        step_back = 0
        while overlap_chars < overlap and step_back < (idx - start_idx):
            step_back += 1
            overlap_chars += len(words[idx - step_back]) + 1
        
        # Next chunk starts at: current_end - overlap
        start_idx = idx - step_back
        
        # Avoid infinite loop if we can't make progress
        if start_idx >= len(words) or step_back == 0:
            break
    
    return chunks
'''

def get_embedding(text: str) -> list[float]:
    """
    Convert text to embedding vector using Azure OpenAI
    
    Args:
        text: Text to embed
        
    Returns:
        List of floats (the embedding vector)
    """
    client = AzureOpenAI(
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=AZURE_OPENAI_API_KEY,
        api_version="2024-02-01"
    )

    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    
    return response.data[0].embedding

def save_chunks_to_file(chunks: list[dict], filename: str = "knowledge_base.json"):
    """
    Save chunks and their embeddings to a JSON file

    Args:
        chunks: List of dicts with 'text' and 'embedding' keys
        filename: Where to save
    """
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(chunks, f, indent=2)
        print(f"Saved {len(chunks)} chunks to {filename}")

def build_knowledge_base(url: str):
    """
    Scrape a URL, chunk it, embed it and save it

    Args:
        url: Website URL to process
    """
    # Step 1: Scrape
    page_data = scrape_page(url)

    # Step 2: Chunk
    text_chunks = chunk_text(page_data['text'])

    # Step 3: Embed each chunk
    chunks_with_embeddings = []
    for i, chunk in enumerate(text_chunks):
        print(f"Embedding chunk {i+1}/{len(text_chunks)}...")
        embedding = get_embedding(chunk)
        chunks_with_embeddings.append({
            'text': chunk,
            'url': url,
            'embedding': embedding
        })

    # Step 4: Save
    save_chunks_to_file(chunks_with_embeddings)
    print("Done!")

def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    """Calculate similarity between two vectors"""
    return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

def search_knowledge_base(query: str, top_k: int = 6) -> str:
    """
    Search the knowledge base for relevant chunks
    
    Args:
        query: User's question
        top_k: How many results to return
        
    Returns:
        Combined text from top matching chunks
    """
    # Load knowledge base
    with open('knowledge_base.json', 'r', encoding='utf-8') as f:
        chunks = json.load(f)
    
    # Get query embedding
    query_embedding = get_embedding(query)
    
    # Calculate similarity for each chunk
    for chunk in chunks:
        chunk['score'] = cosine_similarity(query_embedding, chunk['embedding'])
    
    # Sort by score
    chunks.sort(key=lambda x: x['score'], reverse=True)
    
    # Return top results
    top_chunks = chunks[:top_k]

    # Print scores
    print(f"\n[RAG SEARCH]")
    print(f"Query: {query}")
    print(f"Top {top_k} results (scores):")
    for i, chunk in enumerate(top_chunks):
        print(f"  {i+1}. Score: {chunk['score']:.4f} | Source: {chunk.get('source', 'unknown')}")
        print(f"     Preview: {chunk['text'][:100]}...")
    print(f"[END RAG SEARCH]\n")

    return '\n\n'.join([c['text'] for c in top_chunks])

def add_document_to_knowledge_base(file_path: str, source_name: str):
    """ Add a text file to the existing knowledge base """
    
    # Read the file
    with open(file_path, 'r', encoding='utf-8') as f:
        text = f.read()

    # Chunk the text
    chunks = chunk_text(text)

    # Embed and add metadata
    new_chunks = []
    for  chunk in chunks:
        embedding = get_embedding(chunk)
        new_chunks.append({
            'text': chunk,
            'url': file_path,
            'source': source_name,
            'type': 'document', # vs 'website'
            'embedding': embedding
        })

    # Load existing KB
    with open('knowledge_base.json', 'r') as f:
        existing = json.load(f)

    # Merge and save
    existing.extend(new_chunks)
    save_chunks_to_file(existing)

    print(f"Added {len(new_chunks)} chunks from {file_path}")

if __name__ == "__main__":
   add_document_to_knowledge_base('docs/programs.txt', 'mortgage_programs')
   # Test search
   #result = search_knowledge_base("who was Maria Pilar Mares?")
   #print("Search results:")
   #print(result)
   #build_knowledge_base("https://adelantestory.com")
   '''
   result = scrape_page("https://adelantestory.com")
    chunks = chunk_text(result['text'])
    print(f"Created {len(chunks)} chunks")

    # Test embedding on first chunk
    embedding = get_embedding(chunks[0])
    print(f"Embedding size: {len(embedding)} dimensions")
    print(f"First 5 values: {embedding[:5]}")
   '''

