import customtkinter as ctk
import random, threading, time, ctypes, getpass, platform, sys
from typing import Optional

class EasyConnectOverlay:
    def __init__(self):
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        # Fenster erstellen
        self.root = ctk.CTk()
        self.root.geometry("200x180")       # feste Größe
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
        self.should_stop = False

        # UI aufbauen
        self.setup_ui()
        self.start_status_updates()

        # Fenster nach Start mehrmals nach rechts oben setzen
        for delay in (50, 200, 500):
            self.root.after(delay, self.place_top_right)

        # System-Menü entfernen (nur Windows)
        if self.is_windows:
            self.root.after(100, self.remove_system_menu)

    def on_closing(self):
        """Sauberes Beenden der Anwendung."""
        self.should_stop = True
        self.is_connected = False
        
        # Warten bis Thread beendet ist
        if self.status_thread and self.status_thread.is_alive():
            self.status_thread.join(timeout=1.0)
        
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
        self.status_label = ctk.CTkLabel(self.root, text="● Online",
                                         font=("Segoe UI", 12, "bold"),
                                         text_color="#22c55e")
        self.status_label.pack(pady=(6,2))

        # Aktueller Sprecher
        self.speaker_label = ctk.CTkLabel(self.root, text="Niemand spricht",
                                          font=("Segoe UI", 13, "bold"),
                                          text_color="#eeeeee")
        self.speaker_label.pack(pady=(4,6))

        # Userliste (nur eigener Name)
        self.users_frame = ctk.CTkFrame(self.root, corner_radius=6, fg_color="#111111")
        self.users_frame.pack(fill="both", expand=True, padx=10, pady=6)

        self.update_users_list()

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
        app = EasyConnectOverlay()
        app.run()
    except Exception as e:
        print(f"Kritischer Fehler beim Starten der Anwendung: {e}")
        sys.exit(1) 