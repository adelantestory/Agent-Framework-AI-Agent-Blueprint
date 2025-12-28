import asyncio
from agent import create_agent

async def main():
    # Create the agent
    print("Creating agent...")
    agent = create_agent()

    print("\nAgent ready! Type your message below.")
    print("Type 'quit' or 'exit' to end the conversation.\n")

    # Conversation loop
    while True:
        # Get user input
        user_input = input("You: ")
        # Check if user wants to quit
        if user_input.lower() in ['quit', 'exit']:
            print("Goodbye!")
            break

        # Send message to agent
        result = await agent.run(user_input)

        # Display agent's response
        print(f"Agent: {result.text}\n")


if __name__ == "__main__":
    asyncio.run(main())


