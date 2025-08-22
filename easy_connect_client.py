import customtkinter as ctk
import random, threading, time, ctypes, getpass, platform, sys, requests, json
from typing import Optional
import uuid

class EasyConnectClient:
    def __init__(self, server_url="http://localhost:5000"):
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        # Server configuration
        self.server_url = server_url
        self.client_id = str(uuid.uuid4())
        self.is_connected_to_server = False
        
        # Fenster erstellen
        self.root = ctk.CTk()
        self.root.geometry("250x220")       # Größer für mehr Features
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
        self.should_stop = False

        # UI aufbauen
        self.setup_ui()
        
        # Server verbinden
        self.connect_to_server()
        
        # Threads starten
        self.start_status_updates()
        self.start_heartbeat()

        # Fenster nach Start mehrmals nach rechts oben setzen
        for delay in (50, 200, 500):
            self.root.after(delay, self.place_top_right)

        # System-Menü entfernen (nur Windows)
        if self.is_windows:
            self.root.after(100, self.remove_system_menu)

    def connect_to_server(self):
        """Verbindet sich mit dem Server."""
        try:
            response = requests.post(f"{self.server_url}/api/connect", 
                                   json={
                                       "username": self.local_user,
                                       "client_id": self.client_id
                                   }, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                self.is_connected_to_server = True
                self.connected_users = data.get("connected_users", [self.local_user])
                self.update_status_label("● Online (Server)", "#22c55e")
                print(f"Erfolgreich mit Server verbunden. Benutzer: {self.connected_users}")
            else:
                print(f"Fehler beim Verbinden mit Server: {response.status_code}")
                self.update_status_label("● Offline", "#ef4444")
                
        except requests.exceptions.RequestException as e:
            print(f"Verbindungsfehler: {e}")
            self.update_status_label("● Offline", "#ef4444")
            self.is_connected_to_server = False

    def disconnect_from_server(self):
        """Trennt die Verbindung zum Server."""
        if self.is_connected_to_server:
            try:
                requests.post(f"{self.server_url}/api/disconnect", 
                             json={
                                 "username": self.local_user,
                                 "client_id": self.client_id
                             }, timeout=5)
                self.is_connected_to_server = False
                print("Verbindung zum Server getrennt")
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
        
        # Server-Verbindung trennen
        self.disconnect_from_server()
        
        # Warten bis Threads beendet sind
        if self.status_thread and self.status_thread.is_alive():
            self.status_thread.join(timeout=1.0)
        if self.heartbeat_thread and self.heartbeat_thread.is_alive():
            self.heartbeat_thread.join(timeout=1.0)
        
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

        # Aktueller Sprecher
        self.speaker_label = ctk.CTkLabel(self.root, text="Niemand spricht",
                                          font=("Segoe UI", 13, "bold"),
                                          text_color="#eeeeee")
        self.speaker_label.pack(pady=(4,6))

        # Userliste
        self.users_frame = ctk.CTkFrame(self.root, corner_radius=6, fg_color="#111111")
        self.users_frame.pack(fill="both", expand=True, padx=10, pady=6)

        # Verbindungs-Button
        self.connect_button = ctk.CTkButton(self.root, text="Server verbinden", 
                                           command=self.toggle_server_connection,
                                           height=25)
        self.connect_button.pack(pady=(4,6))

        self.update_users_list()

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
                self.server_status_label.configure(text="Server: Verbunden")

    def update_users_list(self):
        """Aktualisiert die Benutzerliste und den Sprecher-Status."""
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
            
            # Sprecher-Status aktualisieren
            speaker_text = self.current_speaker or "Niemand spricht"
            self.speaker_label.configure(text=speaker_text)
            
        except Exception as e:
            print(f"Fehler beim Aktualisieren der Benutzerliste: {e}")

    def start_status_updates(self):
        """Startet den Status-Update Thread."""
        def loop():
            while not self.should_stop and self.is_connected:
                try:
                    if self.connected_users:
                        if random.random() < 0.15:
                            self.current_speaker = random.choice(self.connected_users)
                            # UI-Updates müssen im Hauptthread erfolgen
                            self.root.after(0, self.update_users_list)
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
                        # Heartbeat an Server senden
                        response = requests.post(f"{self.server_url}/api/heartbeat", 
                                               json={
                                                   "username": self.local_user,
                                                   "client_id": self.client_id
                                               }, timeout=5)
                        
                        if response.status_code == 200:
                            # Benutzerliste vom Server aktualisieren
                            users_response = requests.get(f"{self.server_url}/api/users", timeout=5)
                            if users_response.status_code == 200:
                                users_data = users_response.json()
                                self.connected_users = [user["username"] for user in users_data["users"]]
                                self.current_speaker = users_data.get("current_speaker")
                                self.root.after(0, self.update_users_list)
                        else:
                            print("Heartbeat fehlgeschlagen")
                            self.is_connected_to_server = False
                            self.root.after(0, lambda: self.update_status_label("● Offline", "#ef4444"))
                            self.root.after(0, lambda: self.server_status_label.configure(text="Server: Fehler"))
                    
                    time.sleep(10)  # Alle 10 Sekunden
                    
                except Exception as e:
                    print(f"Fehler im Heartbeat-Thread: {e}")
                    self.is_connected_to_server = False
                    self.root.after(0, lambda: self.update_status_label("● Offline", "#ef4444"))
                    self.root.after(0, lambda: self.server_status_label.configure(text="Server: Fehler"))
                    time.sleep(10)
        
        self.heartbeat_thread = threading.Thread(target=loop, daemon=True)
        self.heartbeat_thread.start()

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
        print(f"Verbinde mit Server: {server_url}")
        
        app = EasyConnectClient(server_url)
        app.run()
    except Exception as e:
        print(f"Kritischer Fehler beim Starten der Anwendung: {e}")
        sys.exit(1) 