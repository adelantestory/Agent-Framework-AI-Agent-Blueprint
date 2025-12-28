import asyncio
import threading
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from agent import create_agent

app = Flask(__name__)
app.secret_key = 'Isaac123!'
CORS(app)

# Store active conversations in memory
# In production, you will want to use Redis or a database
conversations = {}

# Create event loop and agent at startup
loop = asyncio.new_event_loop()

def start_background_loop(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()

# Start event loop in background thread
thread = threading.Thread(target=start_background_loop, args=(loop,), daemon=True)
thread.start()

# Create agent in the background loop
#future = asyncio.run_coroutine_threadsafe(create_agent(), loop)
#agent = future.result()

@app.route('/')
def index():
    """Render the chat interface"""
    return render_template('chat.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    """
    Handle chat messages from the user
    Expected JSON: ["message": "user's message", "session_id": "optional-session-id"
    Returns JSON: {"response": "agent's response", "session_id"
    """
    try:
        # Get the JSON data from the request
        data = request.get_json()
        user_message = data.get('message', '')
        session_id = data.get('session_id', 'default-session')
        
        if not user_message:
            return jsonify({'error': 'No message provided'}), 400
        
        # Get or create agent for this session
        if session_id not in conversations:
            conversations[session_id] = {
                'history': []
            }
        conversation = conversations[session_id]

        # Create a fresh agent for each request
        future = asyncio.run_coroutine_threadsafe(create_agent(), loop)
        fresh_agent = future.result()

        # Get response from agent 
        future = asyncio.run_coroutine_threadsafe(get_agent_response(fresh_agent, user_message), loop)
        response = future.result()

        # Store in history
        conversation['history'].append({
            'user': user_message,
            'agent': response
        })

        return jsonify({
            'response': response,
            'session_id': session_id
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
async def get_agent_response(agent, message):
    """
    Send message to agent and get response
    """
    result = await agent.run(message)
    return result.text
    
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
    
