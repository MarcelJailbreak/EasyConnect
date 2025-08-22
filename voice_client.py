import customtkinter as ctk
import threading, time, ctypes, getpass, platform, sys, json, uuid
import numpy as np
import sounddevice as sd
import webrtcvad
import socketio
from typing import Optional
import queue
import base64

class VoiceChatClient:
    def __init__(self, server_url="http://localhost:5000"):
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        # Server configuration
        self.server_url = server_url
        self.client_id = str(uuid.uuid4())
        self.is_connected_to_server = False
        
        # Audio configuration
        self.sample_rate = 16000  # 16kHz for VAD
        self.chunk_duration = 30  # 30ms chunks
        self.chunk_size = int(self.sample_rate * self.chunk_duration / 1000)
        self.audio_queue = queue.Queue()
        self.is_recording = False
        self.is_muted = False
        self.volume = 1.0
        self.audio_quality = "high"
        
        # Voice Activity Detection
        self.vad = webrtcvad.Vad(2)  # Aggressiveness level 2
        self.is_speaking = False
        self.speaking_threshold = 0.5  # 50% of chunks must contain speech
        
        # Socket.IO client
        self.sio = socketio.Client()
        self.setup_socketio_events()
        
        # Fenster erstellen
        self.root = ctk.CTk()
        self.root.geometry("300x400")       # Größer für Voice-Chat-Features
        self.root.resizable(False, False)
        self.root.attributes("-topmost", True)
        
        # Fenster schließen Event binden
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Platform detection
        self.is_windows = platform.system() == "Windows"

        # Benutzername vom PC
        try:
            self.local_user = getpass.getuser()
        except Exception:
            self.local_user = "Unknown User"

        # Variablen
        self.is_connected = True
        self.connected_users = [self.local_user]
        self.current_speaker = None
        self.status_thread: Optional[threading.Thread] = None
        self.heartbeat_thread: Optional[threading.Thread] = None
        self.audio_thread: Optional[threading.Thread] = None
        self.should_stop = False

        # UI aufbauen
        self.setup_ui()
        
        # Server verbinden
        self.connect_to_server()
        
        # Threads starten
        self.start_status_updates()
        self.start_heartbeat()
        self.start_audio_processing()

        # Fenster nach Start mehrmals nach rechts oben setzen
        for delay in (50, 200, 500):
            self.root.after(delay, self.place_top_right)

        # System-Menü entfernen (nur Windows)
        if self.is_windows:
            self.root.after(100, self.remove_system_menu)

    def setup_socketio_events(self):
        """Setup Socket.IO event handlers."""
        @self.sio.event
        def connect():
            print("Connected to voice server via WebSocket")
            self.join_voice_room("default")
            
        @self.sio.event
        def disconnect():
            print("Disconnected from voice server")
            
        @self.sio.event
        def voice_data(data):
            """Handle incoming voice data from other users."""
            try:
                username = data.get('username')
                audio_data = data.get('audio_data')
                is_speaking = data.get('is_speaking', False)
                
                if username != self.local_user and audio_data and not self.is_muted:
                    # Decode and play audio
                    self.play_audio(audio_data, username)
                    
                # Update UI
                self.root.after(0, self.update_speaker_display, username, is_speaking)
                
            except Exception as e:
                print(f"Error handling voice data: {e}")
                
        @self.sio.event
        def user_joined(data):
            """Handle user joining the voice room."""
            username = data.get('username')
            if username != self.local_user:
                print(f"User {username} joined the voice room")
                self.root.after(0, self.add_user_to_list, username)
                
        @self.sio.event
        def user_left(data):
            """Handle user leaving the voice room."""
            username = data.get('username')
            if username != self.local_user:
                print(f"User {username} left the voice room")
                self.root.after(0, self.remove_user_from_list, username)

    def join_voice_room(self, room_id):
        """Join a voice room via WebSocket."""
        try:
            self.sio.emit('join_room', {
                'room': room_id,
                'username': self.local_user
            })
        except Exception as e:
            print(f"Error joining voice room: {e}")

    def connect_to_server(self):
        """Verbindet sich mit dem Voice-Server."""
        try:
            # Connect via Socket.IO
            self.sio.connect(self.server_url)
            self.is_connected_to_server = True
            self.update_status_label("● Online (Voice)", "#22c55e")
            self.server_status_label.configure(text="Server: Verbunden (Voice)")
            print(f"Erfolgreich mit Voice-Server verbunden")
                
        except Exception as e:
            print(f"Verbindungsfehler: {e}")
            self.update_status_label("● Offline", "#ef4444")
            self.server_status_label.configure(text="Server: Fehler")
            self.is_connected_to_server = False

    def disconnect_from_server(self):
        """Trennt die Verbindung zum Voice-Server."""
        if self.is_connected_to_server:
            try:
                self.sio.disconnect()
                self.is_connected_to_server = False
                print("Verbindung zum Voice-Server getrennt")
            except:
                pass

    def update_status_label(self, text, color):
        """Aktualisiert das Status-Label."""
        try:
            self.status_label.configure(text=text, text_color=color)
        except:
            pass

    def on_closing(self):
        """Sauberes Beenden der Anwendung."""
        self.should_stop = True
        self.is_connected = False
        self.is_recording = False
        
        # Server-Verbindung trennen
        self.disconnect_from_server()
        
        # Warten bis Threads beendet sind
        if self.status_thread and self.status_thread.is_alive():
            self.status_thread.join(timeout=1.0)
        if self.heartbeat_thread and self.heartbeat_thread.is_alive():
            self.heartbeat_thread.join(timeout=1.0)
        if self.audio_thread and self.audio_thread.is_alive():
            self.audio_thread.join(timeout=1.0)
        
        # Fenster zerstören
        self.root.quit()
        self.root.destroy()

    def place_top_right(self):
        """Platziert das Fenster exakt oben rechts."""
        try:
            self.root.update_idletasks()
            sw = self.root.winfo_screenwidth()
            fw = self.root.winfo_width()
            x = sw - fw - 10   # 10px Abstand rechts
            y = 10             # 10px Abstand oben
            self.root.geometry(f"+{x}+{y}")  # nur Position setzen
        except Exception as e:
            print(f"Fehler beim Positionieren: {e}")

    def remove_system_menu(self):
        """Entfernt Minimieren, Maximieren, Schließen (nur Windows)."""
        if not self.is_windows:
            return
            
        try:
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
            style = ctypes.windll.user32.GetWindowLongW(hwnd, -16)
            style &= ~0x00010000  # WS_MINIMIZEBOX
            style &= ~0x00020000  # WS_MAXIMIZEBOX
            style &= ~0x00080000  # WS_SYSMENU
            ctypes.windll.user32.SetWindowLongW(hwnd, -16, style)
        except Exception as e:
            print(f"Fehler beim Entfernen des System-Menüs: {e}")

    def setup_ui(self):
        # Statusanzeige
        self.status_label = ctk.CTkLabel(self.root, text="● Verbinde...",
                                         font=("Segoe UI", 12, "bold"),
                                         text_color="#f59e0b")
        self.status_label.pack(pady=(6,2))

        # Server-Status
        self.server_status_label = ctk.CTkLabel(self.root, text="Server: Unbekannt",
                                               font=("Segoe UI", 10),
                                               text_color="#888888")
        self.server_status_label.pack(pady=(2,4))

        # Voice-Status
        self.voice_status_label = ctk.CTkLabel(self.root, text="🎤 Mikrofon: Bereit",
                                               font=("Segoe UI", 11, "bold"),
                                               text_color="#22c55e")
        self.voice_status_label.pack(pady=(4,6))

        # Aktueller Sprecher
        self.speaker_label = ctk.CTkLabel(self.root, text="Niemand spricht",
                                          font=("Segoe UI", 13, "bold"),
                                          text_color="#eeeeee")
        self.speaker_label.pack(pady=(4,6))

        # Voice-Controls Frame
        self.voice_frame = ctk.CTkFrame(self.root, corner_radius=6, fg_color="#111111")
        self.voice_frame.pack(fill="x", padx=10, pady=6)
        
        # Mute/Unmute Button
        self.mute_button = ctk.CTkButton(self.voice_frame, text="🔇 Stummschalten", 
                                         command=self.toggle_mute,
                                         height=30, fg_color="#dc2626")
        self.mute_button.pack(fill="x", padx=8, pady=4)
        
        # Push-to-Talk Button
        self.ptt_button = ctk.CTkButton(self.voice_frame, text="🎤 Push-to-Talk (Leertaste)", 
                                        command=self.toggle_push_to_talk,
                                        height=30, fg_color="#059669")
        self.ptt_button.pack(fill="x", padx=8, pady=4)

        # Userliste
        self.users_frame = ctk.CTkFrame(self.root, corner_radius=6, fg_color="#111111")
        self.users_frame.pack(fill="both", expand=True, padx=10, pady=6)

        # Verbindungs-Button
        self.connect_button = ctk.CTkButton(self.root, text="Server trennen", 
                                           command=self.toggle_server_connection,
                                           height=25)
        self.connect_button.pack(pady=(4,6))

        # Keyboard bindings
        self.root.bind('<space>', self.on_space_press)
        self.root.bind('<KeyRelease-space>', self.on_space_release)

        self.update_users_list()

    def toggle_mute(self):
        """Wechselt zwischen Stumm und Laut."""
        self.is_muted = not self.is_muted
        if self.is_muted:
            self.mute_button.configure(text="🔊 Stummschaltung aufheben", fg_color="#059669")
            self.voice_status_label.configure(text="🎤 Mikrofon: Stumm", text_color="#ef4444")
        else:
            self.mute_button.configure(text="🔇 Stummschalten", fg_color="#dc2626")
            self.voice_status_label.configure(text="🎤 Mikrofon: Aktiv", text_color="#22c55e")

    def toggle_push_to_talk(self):
        """Wechselt zwischen Push-to-Talk und Voice Activity Detection."""
        if hasattr(self, 'ptt_mode'):
            self.ptt_mode = not self.ptt_mode
        else:
            self.ptt_mode = True
            
        if self.ptt_mode:
            self.ptt_button.configure(text="🎤 Push-to-Talk (Leertaste)", fg_color="#059669")
            self.voice_status_label.configure(text="🎤 Mikrofon: Push-to-Talk", text_color="#22c55e")
        else:
            self.ptt_button.configure(text="🎤 Voice Activity Detection", fg_color="#7c3aed")
            self.voice_status_label.configure(text="🎤 Mikrofon: VAD", text_color="#22c55e")

    def on_space_press(self, event):
        """Handle space key press for Push-to-Talk."""
        if hasattr(self, 'ptt_mode') and self.ptt_mode and not self.is_muted:
            self.start_speaking()

    def on_space_release(self, event):
        """Handle space key release for Push-to-Talk."""
        if hasattr(self, 'ptt_mode') and self.ptt_mode:
            self.stop_speaking()

    def start_speaking(self):
        """Start speaking and update UI."""
        if not self.is_speaking and not self.is_muted:
            self.is_speaking = True
            self.voice_status_label.configure(text="🎤 Mikrofon: SPRECHE", text_color="#f59e0b")
            self.speaker_label.configure(text=f"{self.local_user} spricht")

    def stop_speaking(self):
        """Stop speaking and update UI."""
        if self.is_speaking:
            self.is_speaking = False
            self.voice_status_label.configure(text="🎤 Mikrofon: Aktiv", text_color="#22c55e")
            self.speaker_label.configure(text="Niemand spricht")

    def toggle_server_connection(self):
        """Wechselt zwischen Server-Verbindung und Offline-Modus."""
        if self.is_connected_to_server:
            self.disconnect_from_server()
            self.connect_button.configure(text="Server verbinden")
            self.update_status_label("● Offline", "#ef4444")
            self.server_status_label.configure(text="Server: Getrennt")
        else:
            self.connect_to_server()
            self.connect_button.configure(text="Server trennen")
            if self.is_connected_to_server:
                self.server_status_label.configure(text="Server: Verbunden (Voice)")

    def add_user_to_list(self, username):
        """Fügt einen Benutzer zur Liste hinzu."""
        if username not in self.connected_users:
            self.connected_users.append(username)
            self.update_users_list()

    def remove_user_from_list(self, username):
        """Entfernt einen Benutzer aus der Liste."""
        if username in self.connected_users:
            self.connected_users.remove(username)
            self.update_users_list()

    def update_speaker_display(self, username, is_speaking):
        """Aktualisiert die Sprecher-Anzeige."""
        if is_speaking:
            self.current_speaker = username
            self.speaker_label.configure(text=f"{username} spricht")
        elif self.current_speaker == username:
            self.current_speaker = None
            self.speaker_label.configure(text="Niemand spricht")

    def update_users_list(self):
        """Aktualisiert die Benutzerliste."""
        try:
            # Alte Widgets entfernen
            for w in self.users_frame.winfo_children():
                w.destroy()
            
            # Neue Benutzerliste erstellen
            for user in self.connected_users:
                color = "#ffffff" if user == self.local_user else "#aaaaaa"
                ctk.CTkLabel(self.users_frame, text=user,
                             font=("Segoe UI", 11), text_color=color,
                             anchor="w").pack(anchor="w", pady=4, padx=8)
            
        except Exception as e:
            print(f"Fehler beim Aktualisieren der Benutzerliste: {e}")

    def start_status_updates(self):
        """Startet den Status-Update Thread."""
        def loop():
            while not self.should_stop and self.is_connected:
                try:
                    time.sleep(3)
                except Exception as e:
                    print(f"Fehler im Status-Update Thread: {e}")
                    time.sleep(1)
        
        self.status_thread = threading.Thread(target=loop, daemon=True)
        self.status_thread.start()

    def start_heartbeat(self):
        """Startet den Heartbeat-Thread für Server-Verbindung."""
        def loop():
            while not self.should_stop and self.is_connected:
                try:
                    if self.is_connected_to_server:
                        # Heartbeat über Socket.IO
                        self.sio.emit('heartbeat', {
                            'username': self.local_user,
                            'client_id': self.client_id
                        })
                    
                    time.sleep(10)  # Alle 10 Sekunden
                    
                except Exception as e:
                    print(f"Fehler im Heartbeat-Thread: {e}")
                    time.sleep(10)
        
        self.heartbeat_thread = threading.Thread(target=loop, daemon=True)
        self.heartbeat_thread.start()

    def start_audio_processing(self):
        """Startet den Audio-Verarbeitungs-Thread."""
        def loop():
            while not self.should_stop and self.is_connected:
                try:
                    if self.is_connected_to_server and not self.is_muted:
                        # Audio aufnehmen
                        audio_chunk = sd.rec(self.chunk_size, samplerate=self.sample_rate, 
                                           channels=1, dtype=np.int16)
                        sd.wait()
                        
                        # Voice Activity Detection
                        if hasattr(self, 'ptt_mode') and not self.ptt_mode:
                            # Voice Activity Detection Mode
                            is_speech = self.vad.is_speech(audio_chunk.tobytes(), self.sample_rate)
                            if is_speech and not self.is_speaking:
                                self.start_speaking()
                            elif not is_speech and self.is_speaking:
                                self.stop_speaking()
                        
                        # Audio senden wenn sprechend
                        if self.is_speaking:
                            # Audio komprimieren und senden
                            audio_data = self.compress_audio(audio_chunk)
                            self.sio.emit('voice_data', {
                                'room': 'default',
                                'username': self.local_user,
                                'audio_data': audio_data,
                                'is_speaking': True
                            })
                        else:
                            # Sprecher-Status aktualisieren
                            self.sio.emit('voice_data', {
                                'room': 'default',
                                'username': self.local_user,
                                'audio_data': None,
                                'is_speaking': False
                            })
                    
                    time.sleep(self.chunk_duration / 1000)  # 30ms
                    
                except Exception as e:
                    print(f"Fehler im Audio-Thread: {e}")
                    time.sleep(0.1)
        
        self.audio_thread = threading.Thread(target=loop, daemon=True)
        self.audio_thread.start()

    def compress_audio(self, audio_chunk):
        """Komprimiert Audio-Daten für Übertragung."""
        try:
            # Einfache Kompression: Reduziere Sample-Rate und Quantisierung
            if self.audio_quality == "low":
                # 8kHz, 8-bit
                compressed = audio_chunk[::2].astype(np.int8)
            elif self.audio_quality == "medium":
                # 12kHz, 12-bit
                compressed = audio_chunk[::1.33].astype(np.int16)
            else:
                # 16kHz, 16-bit (original)
                compressed = audio_chunk
            
            # Base64 kodieren für JSON-Übertragung
            return base64.b64encode(compressed.tobytes()).decode('utf-8')
            
        except Exception as e:
            print(f"Fehler bei Audio-Kompression: {e}")
            return ""

    def play_audio(self, audio_data, username):
        """Spielt empfangenes Audio ab."""
        try:
            # Base64 dekodieren
            audio_bytes = base64.b64decode(audio_data)
            audio_array = np.frombuffer(audio_bytes, dtype=np.int16)
            
            # Audio abspielen
            sd.play(audio_array, self.sample_rate)
            
        except Exception as e:
            print(f"Fehler beim Audio-Playback: {e}")

    def run(self):
        """Startet die Hauptschleife der Anwendung."""
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            print("\nAnwendung wird beendet...")
            self.on_closing()
        except Exception as e:
            print(f"Unerwarteter Fehler: {e}")
            self.on_closing()

if __name__ == "__main__":
    try:
        # Server-URL kann als Kommandozeilen-Argument übergeben werden
        server_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5000"
        print(f"Verbinde mit Voice-Server: {server_url}")
        
        app = VoiceChatClient(server_url)
        app.run()
    except Exception as e:
        print(f"Kritischer Fehler beim Starten der Anwendung: {e}")
        sys.exit(1) 