try:
    from flask import Flask, request, jsonify
    from flask_cors import CORS
    from flask_socketio import SocketIO, emit, join_room, leave_room
except ImportError:
    # If the required server libraries are unavailable (e.g. in a restricted
    # environment), inform the user and exit. This prevents runtime
    # tracebacks from confusing users when dependencies are missing.
    print(
        "Die erforderlichen Flask/SocketIO-Bibliotheken sind nicht verfügbar. "
        "Bitte installieren Sie Flask, Flask-CORS und Flask-SocketIO, um den "
        "Voice-Server auszuführen."
    )
    import sys
    sys.exit(1)

import json
import time
import threading
from datetime import datetime
import uuid
import base64
import numpy as np
from collections import defaultdict

app = Flask(__name__)
app.config['SECRET_KEY'] = 'easyconnect_voice_secret_key'
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# In-memory storage for voice chat
connected_users = {}
active_sessions = {}
current_speaker = None
last_activity = {}
voice_rooms = defaultdict(set)  # room_id -> set of user_ids
user_rooms = {}  # user_id -> room_id

class VoiceUser:
    def __init__(self, username, client_id, room_id="default"):
        self.username = username
        self.client_id = client_id
        self.room_id = room_id
        self.connected_at = datetime.now()
        self.last_heartbeat = datetime.now()
        self.is_speaking = False
        self.is_muted = False
        self.volume = 1.0
        self.audio_quality = "high"  # low, medium, high

@app.route('/')
def home():
    """Home endpoint with API information."""
    return jsonify({
        "message": "EasyConnect Voice Server API",
        "version": "2.0.0",
        "features": [
            "Real-time voice chat",
            "Voice Activity Detection",
            "Multiple voice rooms",
            "Audio quality settings",
            "Push-to-Talk support"
        ],
        "endpoints": {
            "POST /api/connect": "Connect a user",
            "POST /api/disconnect": "Disconnect a user", 
            "GET /api/users": "Get all connected users",
            "POST /api/speaker": "Set current speaker",
            "GET /api/status": "Get server status",
            "POST /api/heartbeat": "Update user heartbeat",
            "POST /api/room/join": "Join a voice room",
            "POST /api/room/leave": "Leave a voice room",
            "GET /api/rooms": "Get all voice rooms"
        }
    })

@app.route('/api/connect', methods=['POST'])
def connect_user():
    """Connect a new user to the voice server."""
    try:
        data = request.get_json()
        username = data.get('username')
        client_id = data.get('client_id')
        room_id = data.get('room_id', 'default')
        
        if not username:
            return jsonify({"error": "Username is required"}), 400
            
        if not client_id:
            client_id = str(uuid.uuid4())
        
        # Check if user already exists
        if username in connected_users:
            return jsonify({"error": "Username already taken"}), 409
        
        # Create new voice user
        voice_user = VoiceUser(username, client_id, room_id)
        connected_users[username] = voice_user
        active_sessions[client_id] = username
        last_activity[username] = datetime.now()
        
        # Add user to voice room
        voice_rooms[room_id].add(username)
        user_rooms[username] = room_id
        
        print(f"Voice user {username} connected with client_id: {client_id} to room: {room_id}")
        
        return jsonify({
            "message": "Successfully connected to voice server",
            "client_id": client_id,
            "room_id": room_id,
            "connected_users": list(connected_users.keys()),
            "room_users": list(voice_rooms[room_id]),
            "timestamp": datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        print(f"Error connecting voice user: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/disconnect', methods=['POST'])
def disconnect_user():
    """Disconnect a user from the voice server."""
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
        
        # Remove user from voice room
        voice_user = connected_users[user_to_remove]
        room_id = voice_user.room_id
        if room_id in voice_rooms:
            voice_rooms[room_id].discard(user_to_remove)
        
        # Remove user
        del connected_users[user_to_remove]
        del active_sessions[voice_user.client_id]
        del last_activity[user_to_remove]
        if user_to_remove in user_rooms:
            del user_rooms[user_to_remove]
        
        # Update current speaker if needed
        global current_speaker
        if current_speaker == user_to_remove:
            current_speaker = None
        
        print(f"Voice user {user_to_remove} disconnected from room {room_id}")
        
        return jsonify({
            "message": "Successfully disconnected from voice server",
            "disconnected_user": user_to_remove,
            "remaining_users": list(connected_users.keys()),
            "timestamp": datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        print(f"Error disconnecting voice user: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/room/join', methods=['POST'])
def join_voice_room():
    """Join a voice room."""
    try:
        data = request.get_json()
        username = data.get('username')
        room_id = data.get('room_id', 'default')
        
        if not username:
            return jsonify({"error": "Username is required"}), 400
            
        if username not in connected_users:
            return jsonify({"error": "User not connected"}), 404
        
        # Leave current room
        old_room = connected_users[username].room_id
        if old_room in voice_rooms:
            voice_rooms[old_room].discard(username)
        
        # Join new room
        connected_users[username].room_id = room_id
        voice_rooms[room_id].add(username)
        user_rooms[username] = room_id
        
        print(f"User {username} joined voice room: {room_id}")
        
        return jsonify({
            "message": f"Successfully joined voice room: {room_id}",
            "username": username,
            "room_id": room_id,
            "room_users": list(voice_rooms[room_id]),
            "timestamp": datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        print(f"Error joining voice room: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/rooms', methods=['GET'])
def get_voice_rooms():
    """Get all voice rooms and their users."""
    try:
        rooms_info = {}
        for room_id, users in voice_rooms.items():
            rooms_info[room_id] = {
                "users": list(users),
                "user_count": len(users)
            }
        
        return jsonify({
            "rooms": rooms_info,
            "total_rooms": len(rooms_info),
            "timestamp": datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        print(f"Error getting voice rooms: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/users', methods=['GET'])
def get_users():
    """Get all currently connected voice users."""
    try:
        users_info = []
        for username, voice_user in connected_users.items():
            users_info.append({
                "username": username,
                "room_id": voice_user.room_id,
                "connected_at": voice_user.connected_at.isoformat(),
                "last_heartbeat": voice_user.last_heartbeat.isoformat(),
                "is_speaking": voice_user.is_speaking,
                "is_muted": voice_user.is_muted,
                "volume": voice_user.volume,
                "audio_quality": voice_user.audio_quality
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
                voice_user = connected_users[username]
                del connected_users[username]
                del active_sessions[voice_user.client_id]
                del last_activity[username]
                if username in user_rooms:
                    del user_rooms[username]
                print(f"Removed inactive voice user: {username}")
        
        return jsonify({
            "status": "running",
            "total_users": len(connected_users),
            "total_rooms": len(voice_rooms),
            "current_speaker": current_speaker,
            "server_time": current_time.isoformat(),
            "uptime": "running",
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
        "connected_users": len(connected_users),
        "voice_rooms": len(voice_rooms)
    }), 200

# WebSocket Events für Voice Chat
@socketio.on('connect')
def handle_connect():
    """Handle client connection."""
    print(f"Client connected: {request.sid}")

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection."""
    print(f"Client disconnected: {request.sid}")

@socketio.on('join_room')
def handle_join_room(data):
    """Handle joining a voice room."""
    room = data.get('room')
    username = data.get('username')
    join_room(room)
    emit('user_joined', {'username': username, 'room': room}, room=room)
    print(f"User {username} joined room {room} via WebSocket")

@socketio.on('leave_room')
def handle_leave_room(data):
    """Handle leaving a voice room."""
    room = data.get('room')
    username = data.get('username')
    leave_room(room)
    emit('user_left', {'username': username, 'room': room}, room=room)
    print(f"User {username} left room {room} via WebSocket")

@socketio.on('voice_data')
def handle_voice_data(data):
    """Handle incoming voice data from client."""
    try:
        room = data.get('room')
        username = data.get('username')
        audio_data = data.get('audio_data')
        is_speaking = data.get('is_speaking', False)
        
        # Update speaking status
        if username in connected_users:
            connected_users[username].is_speaking = is_speaking
            
            # Update current speaker globally
            global current_speaker
            if is_speaking:
                current_speaker = username
            elif current_speaker == username:
                current_speaker = None
        
        # Broadcast voice data to other users in the room
        emit('voice_data', {
            'username': username,
            'audio_data': audio_data,
            'is_speaking': is_speaking,
            'timestamp': datetime.now().isoformat()
        }, room=room, include_self=False)
        
    except Exception as e:
        print(f"Error handling voice data: {e}")

@socketio.on('voice_settings')
def handle_voice_settings(data):
    """Handle voice settings updates."""
    try:
        username = data.get('username')
        settings = data.get('settings', {})
        
        if username in connected_users:
            voice_user = connected_users[username]
            
            if 'volume' in settings:
                voice_user.volume = settings['volume']
            if 'audio_quality' in settings:
                voice_user.audio_quality = settings['audio_quality']
            if 'is_muted' in settings:
                voice_user.is_muted = settings['is_muted']
            
            print(f"Updated voice settings for {username}: {settings}")
            
    except Exception as e:
        print(f"Error updating voice settings: {e}")

# -----------------------------------------------------------------------------
# Custom events
# -----------------------------------------------------------------------------

@socketio.on('heartbeat')
def handle_heartbeat(data):
    """
    Update the heartbeat for a connected user. Clients emit this event
    periodically to indicate that they are still active. Without this the
    server relies solely on HTTP heartbeats. This event records the current
    timestamp for the user so that they are not removed by the cleanup thread.
    """
    try:
        username = data.get('username')
        client_id = data.get('client_id')
        if not username:
            return
        if username in connected_users:
            last_activity[username] = datetime.now()
            connected_users[username].last_heartbeat = datetime.now()
    except Exception as e:
        print(f"Error handling heartbeat: {e}")

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
                    voice_user = connected_users[username]
                    del connected_users[username]
                    del active_sessions[voice_user.client_id]
                    del last_activity[username]
                    if username in user_rooms:
                        del user_rooms[username]
                    print(f"Cleanup: Removed inactive voice user: {username}")
            
            time.sleep(30)  # Check every 30 seconds
            
        except Exception as e:
            print(f"Error in cleanup thread: {e}")
            time.sleep(30)

if __name__ == '__main__':
    # Start cleanup thread
    cleanup_thread = threading.Thread(target=cleanup_inactive_users, daemon=True)
    cleanup_thread.start()
    
    print("Starting EasyConnect Voice Server...")
    print("Server will be available at: http://localhost:5000")
    print("WebSocket support enabled for real-time voice chat")
    
    # For production on Render, use:
    # socketio.run(app, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
    socketio.run(app, host='0.0.0.0', port=5000, debug=False) 