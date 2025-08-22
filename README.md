# EasyConnect - Real-Time Voice Chat Overlay 🎤

Ein **echter Voice-Chat** mit Overlay, der in Echtzeit Audio zwischen Benutzern überträgt und den aktuellen Sprecher anzeigt.

## 🚀 **Features**

- **🎤 Echter Voice-Chat**: Mikrofon-Aufnahme und Audio-Übertragung
- **🔊 Voice Activity Detection**: Automatische Erkennung wer spricht
- **⌨️ Push-to-Talk**: Leertaste zum Sprechen
- **🎵 Audio-Qualitäts-Einstellungen**: Low/Medium/High Quality
- **🔇 Mute/Unmute**: Stummschaltung für einzelne Benutzer
- **🏠 Voice Rooms**: Mehrere Sprachkanäle
- **📡 WebSocket**: Echtzeit-Kommunikation
- **🌐 Cross-Platform**: Windows, macOS, Linux
- **🎨 Dark Theme**: Modernes, dunkles Design

## 📁 **Projektstruktur**

```
esc/
├── voice_server.py              # Voice-Chat Server mit WebSocket
├── voice_client.py              # Voice-Chat Client mit Mikrofon
├── easy_connect_overlay.py      # Standalone Overlay (ohne Voice)
├── easy_connect_client.py       # Client ohne Voice (nur Status)
├── server.py                    # Alter Server (ohne Voice)
├── requirements.txt             # Python-Abhängigkeiten
├── render.yaml                  # Render Deployment-Konfiguration
└── README.md                    # Diese Datei
```

## 🛠️ **Installation**

### **Voraussetzungen**

- Python 3.8 oder höher
- pip (Python Package Manager)
- **Mikrofon** (für Voice-Chat)
- **Lautsprecher/Kopfhörer** (für Audio-Playback)

### **Lokale Installation**

1. **Repository klonen oder Dateien herunterladen**
2. **Abhängigkeiten installieren:**
   ```bash
   pip install -r requirements.txt
   ```

### **Wichtige Audio-Abhängigkeiten**

```bash
# Für Windows (falls PyAudio Probleme macht)
pip install pipwin
pipwin install pyaudio

# Für macOS
brew install portaudio
pip install pyaudio

# Für Linux
sudo apt-get install portaudio19-dev python3-pyaudio
pip install pyaudio
```

## 🚀 **Verwendung**

### **1. Voice-Chat Server starten**
```bash
python voice_server.py
```
- Server läuft auf `http://localhost:5000`
- WebSocket-Support für Echtzeit-Audio
- Verwaltet Voice-Rooms und Benutzer

### **2. Voice-Chat Client starten**
```bash
# Mit lokalem Server
python voice_client.py

# Mit spezifischer Server-URL
python voice_client.py http://localhost:5000
```

### **3. Standalone Overlay (ohne Voice)**
```bash
python easy_connect_overlay.py
```

## 🎤 **Voice-Chat Features**

### **Mikrofon-Steuerung**
- **🔇 Stummschalten**: Mikrofon komplett deaktivieren
- **🎤 Push-to-Talk**: Nur bei gedrückter Leertaste sprechen
- **🎵 Voice Activity Detection**: Automatische Sprecher-Erkennung

### **Audio-Qualität**
- **Low**: 8kHz, 8-bit (weniger Bandbreite)
- **Medium**: 12kHz, 12-bit (ausgewogen)
- **High**: 16kHz, 16-bit (beste Qualität)

### **Voice Rooms**
- **Standard-Room**: "default"
- **Mehrere Kanäle**: Für verschiedene Gruppen
- **Room-Wechsel**: Benutzer können zwischen Räumen wechseln

## 🌐 **Deployment auf Render**

### **Automatisches Deployment**

1. **Repository auf GitHub hochladen**
2. **Bei Render anmelden** (https://render.com)
3. **Neuen Web Service erstellen**
4. **GitHub Repository verbinden**
5. **Automatisches Deployment starten**

### **Konfiguration für Voice-Server**

```yaml
# render.yaml
services:
  - type: web
    name: easyconnect-voice-server
    env: python
    plan: free
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn --worker-class eventlet -w 1 voice_server:app
    envVars:
      - key: PYTHON_VERSION
        value: 3.9.16
```

## 🔧 **API Endpoints**

### **Voice Server API**

- `GET /` - API Informationen
- `POST /api/connect` - Benutzer verbinden
- `POST /api/disconnect` - Benutzer trennen
- `GET /api/users` - Alle verbundenen Benutzer
- `POST /api/room/join` - Voice-Room beitreten
- `GET /api/rooms` - Alle Voice-Rooms
- `GET /api/status` - Server-Status
- `POST /api/heartbeat` - Heartbeat senden
- `GET /health` - Health Check für Render

### **WebSocket Events**

- `connect` - Client verbindet sich
- `disconnect` - Client trennt sich
- `join_room` - Voice-Room beitreten
- `leave_room` - Voice-Room verlassen
- `voice_data` - Audio-Daten senden/empfangen
- `voice_settings` - Audio-Einstellungen aktualisieren

## 🎮 **Verwendung**

### **Overlay-Fenster**

- **Position**: Wird automatisch oben rechts positioniert
- **Größe**: 300x400 Pixel (Voice-Client)
- **Always-on-top**: Bleibt über anderen Fenstern
- **Keine System-Buttons**: Minimieren/Maximieren/Schließen deaktiviert

### **Voice-Status-Anzeigen**

- **🎤 Mikrofon: Bereit** - Mikrofon funktionsfähig
- **🎤 Mikrofon: Aktiv** - Mikrofon aktiviert
- **🎤 Mikrofon: SPRECHE** - Benutzer spricht gerade
- **🎤 Mikrofon: Stumm** - Mikrofon deaktiviert

### **Steuerung**

- **Leertaste**: Push-to-Talk (wenn aktiviert)
- **Mute-Button**: Mikrofon stummschalten
- **PTT-Button**: Zwischen Push-to-Talk und VAD wechseln

## 🔒 **Sicherheit & Datenschutz**

- **Keine Audio-Speicherung**: Audio wird nicht auf dem Server gespeichert
- **Ende-zu-Ende**: Audio wird direkt zwischen Clients übertragen
- **Keine Authentifizierung**: Für Demo-Zwecke (kann erweitert werden)
- **CORS aktiviert**: Für lokale Entwicklung

## 🐛 **Bekannte Probleme & Lösungen**

### **1. PyAudio Installation**
- **Problem**: PyAudio lässt sich nicht installieren
- **Lösung**: PortAudio vorher installieren (siehe Installation)

### **2. Mikrofon-Zugriff**
- **Problem**: Kein Mikrofon-Zugriff
- **Lösung**: Browser-Berechtigungen prüfen, Mikrofon freigeben

### **3. Audio-Latenz**
- **Problem**: Hohe Verzögerung bei Audio
- **Lösung**: Audio-Qualität auf "Low" setzen, Netzwerk prüfen

### **4. WebSocket-Verbindung**
- **Problem**: WebSocket-Verbindung schlägt fehl
- **Lösung**: Server läuft, Firewall-Einstellungen prüfen

## 🔍 **Debugging**

### **Logs aktivieren**

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### **Audio-Test**

```bash
# Teste Mikrofon
python -c "import sounddevice as sd; print(sd.query_devices())"

# Teste Audio-Playback
python -c "import sounddevice as sd; sd.play(sd.rec(16000, samplerate=16000, channels=1, dtype='int16'), 16000)"
```

## 🚀 **Nächste Schritte**

### **Verbesserungen**

1. **🔐 Authentifizierung**: Benutzer-Login-System
2. **🔒 Verschlüsselung**: SSL/TLS für sichere Kommunikation
3. **📱 Mobile App**: React Native oder Flutter Client
4. **🎵 Audio-Filter**: Echo-Cancellation, Noise Reduction
5. **📹 Video-Chat**: Webcam-Integration

### **Skalierung**

1. **⚡ Redis**: Session-Management und Caching
2. **🐳 Docker**: Containerisierung für einfaches Deployment
3. **📊 Monitoring**: Audio-Qualitäts-Metriken
4. **🌍 CDN**: Globale Audio-Verteilung

## 📞 **Support**

Bei Problemen oder Fragen:

1. **Issues auf GitHub erstellen**
2. **Logs überprüfen** (Konsolen-Ausgabe)
3. **Server-Status testen** (`/health` Endpoint)
4. **Audio-Geräte prüfen** (Mikrofon, Lautsprecher)
5. **Netzwerk-Verbindung testen**

## 📄 **Lizenz**

Dieses Projekt ist für Bildungs- und Demo-Zwecke erstellt. Freie Verwendung erlaubt.

---

**🎉 Jetzt kannst du wirklich sprechen und hören! 🎤🔊** 