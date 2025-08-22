from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import time
import threading
from datetime import datetime
import uuid

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# In-memory storage for demo purposes
# In production, use a proper database like PostgreSQL
connected_users = {}
active_sessions = {}
current_speaker = None
last_activity = {}

class UserSession:
    def __init__(self, username, client_id):
        self.username = username
        self.client_id = client_id
        self.connected_at = datetime.now()
        self.last_heartbeat = datetime.now()
        self.is_speaking = False

@app.route('/')
def home():
    """Home endpoint with API information."""
    return jsonify({
        "message": "EasyConnect Server API",
        "version": "1.0.0",
        "endpoints": {
            "POST /api/connect": "Connect a user",
            "POST /api/disconnect": "Disconnect a user", 
            "GET /api/users": "Get all connected users",
            "POST /api/speaker": "Set current speaker",
            "GET /api/status": "Get server status",
            "POST /api/heartbeat": "Update user heartbeat"
        }
    })

@app.route('/api/connect', methods=['POST'])
def connect_user():
    """Connect a new user to the server."""
    try:
        data = request.get_json()
        username = data.get('username')
        client_id = data.get('client_id')
        
        if not username:
            return jsonify({"error": "Username is required"}), 400
            
        if not client_id:
            client_id = str(uuid.uuid4())
        
        # Check if user already exists
        if username in connected_users:
            return jsonify({"error": "Username already taken"}), 409
        
        # Create new user session
        user_session = UserSession(username, client_id)
        connected_users[username] = user_session
        active_sessions[client_id] = username
        last_activity[username] = datetime.now()
        
        print(f"User {username} connected with client_id: {client_id}")
        
        return jsonify({
            "message": "Successfully connected",
            "client_id": client_id,
            "connected_users": list(connected_users.keys()),
            "timestamp": datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        print(f"Error connecting user: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/disconnect', methods=['POST'])
def disconnect_user():
    """Disconnect a user from the server."""
    try:
        data = request.get_json()
        username = data.get('username')
        client_id = data.get('client_id')
        
        if not username and not client_id:
            return jsonify({"error": "Username or client_id is required"}), 400
        
        # Find user to disconnect
        user_to_remove = None
        if username and username in connected_users:
            user_to_remove = username
        elif client_id and client_id in active_sessions:
            user_to_remove = active_sessions[client_id]
        
        if not user_to_remove:
            return jsonify({"error": "User not found"}), 404
        
        # Remove user
        user_session = connected_users[user_to_remove]
        del connected_users[user_to_remove]
        del active_sessions[user_session.client_id]
        del last_activity[user_to_remove]
        
        # Update current speaker if needed
        global current_speaker
        if current_speaker == user_to_remove:
            current_speaker = None
        
        print(f"User {user_to_remove} disconnected")
        
        return jsonify({
            "message": "Successfully disconnected",
            "disconnected_user": user_to_remove,
            "remaining_users": list(connected_users.keys()),
            "timestamp": datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        print(f"Error disconnecting user: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/users', methods=['GET'])
def get_users():
    """Get all currently connected users."""
    try:
        users_info = []
        for username, session in connected_users.items():
            users_info.append({
                "username": username,
                "connected_at": session.connected_at.isoformat(),
                "last_heartbeat": session.last_heartbeat.isoformat(),
                "is_speaking": session.is_speaking
            })
        
        return jsonify({
            "users": users_info,
            "total_users": len(users_info),
            "current_speaker": current_speaker,
            "timestamp": datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        print(f"Error getting users: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/speaker', methods=['POST'])
def set_speaker():
    """Set the current speaker."""
    try:
        data = request.get_json()
        username = data.get('username')
        
        if not username:
            return jsonify({"error": "Username is required"}), 400
            
        if username not in connected_users:
            return jsonify({"error": "User not connected"}), 404
        
        global current_speaker
        old_speaker = current_speaker
        
        # Update speaker status
        if current_speaker and current_speaker in connected_users:
            connected_users[current_speaker].is_speaking = False
            
        current_speaker = username
        connected_users[username].is_speaking = True
        
        print(f"Speaker changed from {old_speaker} to {username}")
        
        return jsonify({
            "message": "Speaker updated",
            "current_speaker": username,
            "previous_speaker": old_speaker,
            "timestamp": datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        print(f"Error setting speaker: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/status', methods=['GET'])
def get_status():
    """Get server status and statistics."""
    try:
        # Clean up inactive users (more than 30 seconds without heartbeat)
        current_time = datetime.now()
        inactive_users = []
        
        for username, last_seen in last_activity.items():
            if (current_time - last_seen).total_seconds() > 30:
                inactive_users.append(username)
        
        # Remove inactive users
        for username in inactive_users:
            if username in connected_users:
                user_session = connected_users[username]
                del connected_users[username]
                del active_sessions[user_session.client_id]
                del last_activity[username]
                print(f"Removed inactive user: {username}")
        
        return jsonify({
            "status": "running",
            "total_users": len(connected_users),
            "current_speaker": current_speaker,
            "server_time": current_time.isoformat(),
            "uptime": "running",  # In production, track actual uptime
            "timestamp": datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        print(f"Error getting status: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/heartbeat', methods=['POST'])
def update_heartbeat():
    """Update user heartbeat to keep them connected."""
    try:
        data = request.get_json()
        username = data.get('username')
        client_id = data.get('client_id')
        
        if not username:
            return jsonify({"error": "Username is required"}), 400
            
        if username not in connected_users:
            return jsonify({"error": "User not connected"}), 404
        
        # Update heartbeat
        last_activity[username] = datetime.now()
        connected_users[username].last_heartbeat = datetime.now()
        
        return jsonify({
            "message": "Heartbeat updated",
            "username": username,
            "timestamp": datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        print(f"Error updating heartbeat: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/health')
def health_check():
    """Health check endpoint for Render."""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "connected_users": len(connected_users)
    }), 200

# Cleanup thread for inactive users
def cleanup_inactive_users():
    """Background thread to clean up inactive users."""
    while True:
        try:
            current_time = datetime.now()
            inactive_users = []
            
            for username, last_seen in last_activity.items():
                if (current_time - last_seen).total_seconds() > 60:  # 1 minute timeout
                    inactive_users.append(username)
            
            # Remove inactive users
            for username in inactive_users:
                if username in connected_users:
                    user_session = connected_users[username]
                    del connected_users[username]
                    del active_sessions[user_session.client_id]
                    del last_activity[username]
                    print(f"Cleanup: Removed inactive user: {username}")
            
            time.sleep(30)  # Check every 30 seconds
            
        except Exception as e:
            print(f"Error in cleanup thread: {e}")
            time.sleep(30)

if __name__ == '__main__':
    # Start cleanup thread
    cleanup_thread = threading.Thread(target=cleanup_inactive_users, daemon=True)
    cleanup_thread.start()
    
    print("Starting EasyConnect Server...")
    print("Server will be available at: http://localhost:5000")
    
    # For production on Render, use:
    # app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
    app.run(host='0.0.0.0', port=5000, debug=False) 