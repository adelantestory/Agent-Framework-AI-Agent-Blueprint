import asyncio
from agent import create_agent

async def test_agent():
    """Test if the agent has tools registered"""
    print("Creating agent...")
    agent = await create_agent()

    # Check if agent has tools
    print(f"\nAgent name: {agent.name}")
    print(f"Agent ID: {agent.id}")

    # Try to inspect the agent's properties
    print(f"\nAgent type: {type(agent)}")
    print(f"Agent attributes: {[attr for attr in dir(agent) if not attr.startswith('__')][:10]}...")

    # Test with a simple calculation question
    print("\n" + "="*50)
    print("Testing with: 'What is 10 + 5?'")
    print("="*50)

    result = await agent.run("What is 10 + 5?")
    print(f"\nResponse: {result.text}")

    # Test with knowledge base question
    print("\n" + "="*50)
    print("Testing with: 'What mortgage programs are available?'")
    print("="*50)

    result = await agent.run("What mortgage programs are available?")
    print(f"\nResponse: {result.text}")

    # Test for Rentcast MCP tool
    print("\n" + "="*50)
    print("Testing with: 'What is the median rent in Austin, Tx?'")
    print("="*50)

    result = await agent.run("What is the median rent in Austin, Tx?")
    print(f"\nResponse: {result.text}")


if __name__ == "__main__":
    asyncio.run(test_agent())