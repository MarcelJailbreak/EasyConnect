# EasyConnect - Voice Chat Overlay

Ein modernes Voice Chat Overlay mit Server-Client-Architektur, das in Echtzeit den aktuellen Sprecher und verbundene Benutzer anzeigt.

## 🚀 Features

- **Real-time Overlay**: Zeigt aktuelle Sprecher und verbundene Benutzer an
- **Server-Client Architektur**: Zentrale Verwaltung aller Verbindungen
- **Automatische Positionierung**: Fenster wird automatisch oben rechts positioniert
- **Cross-Platform**: Funktioniert auf Windows, macOS und Linux
- **Dark Theme**: Modernes, dunkles Design
- **Heartbeat System**: Automatische Verbindungsüberwachung
- **Graceful Shutdown**: Sauberes Beenden aller Threads

## 📁 Projektstruktur

```
esc/
├── easy_connect_overlay.py      # Standalone Overlay (ohne Server)
├── easy_connect_client.py       # Client mit Server-Verbindung
├── server.py                    # Flask Server für Render
├── requirements.txt             # Python-Abhängigkeiten
├── render.yaml                  # Render Deployment-Konfiguration
└── README.md                    # Diese Datei
```

## 🛠️ Installation

### Voraussetzungen

- Python 3.8 oder höher
- pip (Python Package Manager)

### Lokale Installation

1. **Repository klonen oder Dateien herunterladen**
2. **Abhängigkeiten installieren:**
   ```bash
   pip install -r requirements.txt
   ```

### Zusätzliche Abhängigkeiten für Client

```bash
pip install requests
```

## 🚀 Verwendung

### 1. Standalone Overlay (ohne Server)

```bash
python easy_connect_overlay.py
```

### 2. Client mit Server-Verbindung

```bash
# Lokaler Server
python easy_connect_client.py

# Mit spezifischer Server-URL
python easy_connect_client.py http://localhost:5000
```

### 3. Server starten

```bash
python server.py
```

Der Server läuft dann auf `http://localhost:5000`

## 🌐 Deployment auf Render

### Automatisches Deployment

1. **Repository auf GitHub hochladen**
2. **Bei Render anmelden** (https://render.com)
3. **Neuen Web Service erstellen**
4. **GitHub Repository verbinden**
5. **Automatisches Deployment starten**

### Manuelles Deployment

1. **Render Dashboard öffnen**
2. **"New Web Service" klicken**
3. **Repository verbinden**
4. **Konfiguration:**
   - **Name**: `easyconnect-server`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn server:app`
   - **Plan**: Free (für den Start)

### Environment Variables

```bash
PYTHON_VERSION=3.9.16
```

## 🔧 API Endpoints

### Server API

- `GET /` - API Informationen
- `POST /api/connect` - Benutzer verbinden
- `POST /api/disconnect` - Benutzer trennen
- `GET /api/users` - Alle verbundenen Benutzer
- `POST /api/speaker` - Aktuellen Sprecher setzen
- `GET /api/status` - Server-Status
- `POST /api/heartbeat` - Heartbeat senden
- `GET /health` - Health Check für Render

### Beispiel API-Aufrufe

```bash
# Benutzer verbinden
curl -X POST http://localhost:5000/api/connect \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser"}'

# Alle Benutzer abrufen
curl http://localhost:5000/api/users

# Sprecher setzen
curl -X POST http://localhost:5000/api/speaker \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser"}'
```

## 🐛 Bekannte Probleme & Lösungen

### 1. Threading-Probleme behoben
- **Problem**: Threads liefen endlos weiter
- **Lösung**: Saubere Thread-Verwaltung mit `should_stop` Flag

### 2. Memory Leaks verhindert
- **Problem**: Widgets wurden nicht aufgeräumt
- **Lösung**: Proper cleanup in `update_users_list()`

### 3. Platform-spezifische Fehler
- **Problem**: Windows-spezifischer Code auf anderen Plattformen
- **Lösung**: Platform-Detection und bedingte Ausführung

### 4. Graceful Shutdown
- **Problem**: Anwendung konnte nicht sauber beendet werden
- **Lösung**: `on_closing()` Methode mit Thread-Cleanup

### 5. Exception Handling
- **Problem**: Fehler führten zu Abstürzen
- **Lösung**: Try-catch Blöcke in allen kritischen Bereichen

## 🔍 Debugging

### Logs aktivieren

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Häufige Fehler

1. **Port bereits belegt**: Anderen Port wählen oder laufenden Prozess beenden
2. **Firewall-Blockierung**: Port 5000 freigeben
3. **CORS-Fehler**: Server läuft nicht oder CORS nicht aktiviert

## 📱 Verwendung

### Overlay-Fenster

- **Position**: Wird automatisch oben rechts positioniert
- **Größe**: 250x220 Pixel (Client) / 200x180 Pixel (Standalone)
- **Always-on-top**: Bleibt über anderen Fenstern
- **Keine System-Buttons**: Minimieren/Maximieren/Schließen deaktiviert

### Status-Anzeigen

- **● Online (Server)**: Verbunden mit Server
- **● Offline**: Keine Server-Verbindung
- **● Verbinde...**: Verbindungsaufbau läuft

### Benutzerliste

- **Eigener Name**: Weiß hervorgehoben
- **Andere Benutzer**: Grau dargestellt
- **Aktueller Sprecher**: Wird in der Mitte angezeigt

## 🔒 Sicherheit

- **Keine Authentifizierung**: Für Demo-Zwecke
- **In-Memory Storage**: Daten gehen bei Neustart verloren
- **CORS aktiviert**: Für lokale Entwicklung
- **Timeout-Handling**: Automatische Bereinigung inaktiver Benutzer

## 🚀 Nächste Schritte

### Verbesserungen

1. **Datenbank-Integration**: PostgreSQL für persistente Daten
2. **WebSocket**: Echtzeit-Updates ohne Polling
3. **Authentifizierung**: Benutzer-Login-System
4. **Verschlüsselung**: SSL/TLS für sichere Kommunikation
5. **Mobile App**: React Native oder Flutter Client

### Skalierung

1. **Load Balancer**: Mehrere Server-Instanzen
2. **Redis**: Session-Management und Caching
3. **Docker**: Containerisierung für einfaches Deployment
4. **Monitoring**: Logs und Metriken

## 📞 Support

Bei Problemen oder Fragen:

1. **Issues auf GitHub erstellen**
2. **Logs überprüfen** (Konsolen-Ausgabe)
3. **Server-Status testen** (`/health` Endpoint)
4. **Browser-Entwicklertools** für API-Aufrufe

## 📄 Lizenz

Dieses Projekt ist für Bildungs- und Demo-Zwecke erstellt. Freie Verwendung erlaubt.

---

**Viel Erfolg mit EasyConnect! 🎉** 