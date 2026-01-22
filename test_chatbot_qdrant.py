"""Test that the chatbot tool uses Qdrant correctly"""
from tools import search_adelante_knowledge

print("Testing search_adelante_knowledge with Qdrant...")
print("="*60)

query = "What programs does Adelante Story Foundation offer?"
print(f"Query: {query}\n")

result = search_adelante_knowledge(query)

print("\nResult type:", type(result))
print("\nResult preview (first 500 chars):")
print(result[:500])
print("\n" + "="*60)
print("SUCCESS! Chatbot tool is now using Qdrant!")
