import asyncio
import websockets
import json
import logging
from datetime import datetime
import base64
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ChatRoom:
    def __init__(self):
        self.clients = {}  # {websocket: {'username': str, 'joined': datetime}}
        self.messages = []  # Store recent messages
        self.max_messages = 100
        
    async def register(self, websocket, username):
        """Register a new client"""
        self.clients[websocket] = {
            'username': username,
            'joined': datetime.now()
        }
        logger.info(f"User {username} joined the chat")
        
        # Send welcome message
        welcome_msg = {
            'type': 'system',
            'message': f'Willkommen {username}! Du bist jetzt verbunden.',
            'timestamp': datetime.now().isoformat()
        }
        await websocket.send(json.dumps(welcome_msg))
        
        # Notify other clients
        await self.notify_user_joined(username)
        
        # Send current online users
        await self.send_online_users(websocket)
        
    async def unregister(self, websocket):
        """Unregister a client"""
        if websocket in self.clients:
            username = self.clients[websocket]['username']
            del self.clients[websocket]
            logger.info(f"User {username} left the chat")
            await self.notify_user_left(username)
            
    async def notify_user_joined(self, username):
        """Notify all clients that a user joined"""
        message = {
            'type': 'user_joined',
            'username': username,
            'timestamp': datetime.now().isoformat()
        }
        await self.broadcast(json.dumps(message))
        
    async def notify_user_left(self, username):
        """Notify all clients that a user left"""
        message = {
            'type': 'user_left',
            'username': username,
            'timestamp': datetime.now().isoformat()
        }
        await self.broadcast(json.dumps(message))
        
    async def send_online_users(self, websocket):
        """Send list of online users to a specific client"""
        users = [client['username'] for client in self.clients.values()]
        message = {
            'type': 'online_users',
            'users': users,
            'timestamp': datetime.now().isoformat()
        }
        await websocket.send(json.dumps(message))
        
    async def broadcast(self, message):
        """Send message to all connected clients"""
        if self.clients:
            await asyncio.gather(
                *[client.send(message) for client in self.clients.keys()]
            )
            
    async def handle_message(self, websocket, message_data):
        """Handle incoming messages"""
        try:
            data = json.loads(message_data)
            msg_type = data.get('type')
            
            if msg_type == 'chat':
                # Handle chat message
                username = self.clients[websocket]['username']
                message = data.get('message', '')
                
                chat_msg = {
                    'type': 'chat',
                    'username': username,
                    'message': message,
                    'timestamp': datetime.now().isoformat()
                }
                
                # Store message
                self.messages.append(chat_msg)
                if len(self.messages) > self.max_messages:
                    self.messages.pop(0)
                    
                # Broadcast to all clients
                await self.broadcast(json.dumps(chat_msg))
                
            elif msg_type == 'file':
                # Handle file sharing
                username = self.clients[websocket]['username']
                filename = data.get('filename', '')
                file_data = data.get('file_data', '')
                
                file_msg = {
                    'type': 'file',
                    'username': username,
                    'filename': filename,
                    'file_data': file_data,
                    'timestamp': datetime.now().isoformat()
                }
                
                # Broadcast file to all clients
                await self.broadcast(json.dumps(file_msg))
                
            elif msg_type == 'voice':
                # Handle voice data
                username = self.clients[websocket]['username']
                voice_data = data.get('voice_data', '')
                
                voice_msg = {
                    'type': 'voice',
                    'username': username,
                    'voice_data': voice_data,
                    'timestamp': datetime.now().isoformat()
                }
                
                # Broadcast voice to other clients
                await self.broadcast_to_others(websocket, json.dumps(voice_msg))
                
            elif msg_type == 'video':
                # Handle video data
                username = self.clients[websocket]['username']
                video_data = data.get('video_data', '')
                
                video_msg = {
                    'type': 'video',
                    'username': username,
                    'video_data': video_data,
                    'timestamp': datetime.now().isoformat()
                }
                
                # Broadcast video to other clients
                await self.broadcast_to_others(websocket, json.dumps(video_msg))
                
        except json.JSONDecodeError:
            logger.error("Invalid JSON received")
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            
    async def broadcast_to_others(self, sender_websocket, message):
        """Send message to all clients except sender"""
        other_clients = [client for client in self.clients.keys() if client != sender_websocket]
        if other_clients:
            await asyncio.gather(
                *[client.send(message) for client in other_clients]
            )

# Global chat room instance
chat_room = ChatRoom()

async def handle_client(websocket, path):
    """Handle individual client connections"""
    try:
        # Wait for username registration
        async for message in websocket:
            try:
                data = json.loads(message)
                if data.get('type') == 'register':
                    username = data.get('username', 'Anonymous')
                    await chat_room.register(websocket, username)
                    break
            except json.JSONDecodeError:
                continue
                
        # Main message handling loop
        async for message in websocket:
            await chat_room.handle_message(websocket, message)
            
    except websockets.exceptions.ConnectionClosed:
        logger.info("Client connection closed")
    except Exception as e:
        logger.error(f"Error handling client: {e}")
    finally:
        await chat_room.unregister(websocket)

async def main():
    """Main server function"""
    # Get port from environment variable (for onrender)
    port = int(os.environ.get('PORT', 8765))
    
    logger.info(f"Starting EasyConnect server on port {port}")
    
    # Start WebSocket server
    async with websockets.serve(handle_client, "0.0.0.0", port):
        logger.info(f"Server is running on port {port}")
        await asyncio.Future()  # Run forever

if __name__ == "__main__":
    asyncio.run(main()) 