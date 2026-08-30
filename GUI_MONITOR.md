# Smart Meter Live GUI Monitor

## Wichtiger Hinweis

**Die Live-GUI benötigt eine grafische Umgebung (Desktop)!**

Wenn Sie das System über SSH verwenden oder auf einem Server ohne Desktop arbeiten:
- ✗ Die GUI wird **nicht** funktionieren
- ✓ Verwenden Sie stattdessen `plot_power_data.py` für statische PNG-Grafiken
- ✓ Oder verwenden Sie SSH mit X11-Forwarding: `ssh -X user@host`

## Schnellstart

### Option 1: Mit Smart Meter (Live-Daten)

```bash
# Starte mit Live-GUI
python3 readout-smart-meter.py --gui

# Zeige letzte 2 Stunden
python3 readout-smart-meter.py --gui --gui-hours 2
```

### Option 2: GUI separat starten

```bash
# Erst Datenerfassung starten
python3 readout-smart-meter.py

# In einem anderen Terminal: GUI starten
python3 live_monitor.py --hours 1
```

### Option 3: Demo mit simulierten Daten

```bash
# Teste die GUI ohne Hardware
python3 demo_gui.py
```

## Kommandozeilen-Optionen

### readout-smart-meter.py

```
--gui              Startet Live-GUI automatisch
--gui-hours N      Zeigt letzte N Stunden im GUI (Standard: 1)
--log-interval N   Logge jede N-te Messung (Standard: 1)
--clear-data       Löscht alte Daten und startet neu (erstellt Backup)
--key KEY          AES-Schlüssel für Entschlüsselung
--port PORT        Serieller Port (Standard: /dev/ttyUSB0)
```

### live_monitor.py

```
--hours N          Anzahl der anzuzeigenden Stunden (Standard: 1)
--interval MS      Update-Intervall in Millisekunden (Standard: 5000)
--file FILE        Pfad zur CSV-Datei (Standard: power_data.csv)
```

## Funktionen

Das Live-GUI zeigt:
- ✓ Netto-Leistung in Echtzeit (oberer Graph)
- ✓ Bezug und Einspeisung getrennt (unterer Graph)
- ✓ Aktuelle Werte, Durchschnitt, Min/Max
- ✓ Automatische Updates alle 5 Sekunden
- ✓ Zeitachse mit Uhrzeiten

## Beispiele

```bash
# Neu starten (alte Daten löschen)
python3 readout-smart-meter.py --clear-data --gui

# Zeige letzte 30 Minuten
python3 readout-smart-meter.py --gui --gui-hours 0.5

# Logge nur jede Minute mit GUI
python3 readout-smart-meter.py --gui --log-interval 12

# Zeige letzte 6 Stunden (separat)
python3 live_monitor.py --hours 6

# Schnellere Updates (alle 2 Sekunden)
python3 live_monitor.py --interval 2000

# Eigene Datendatei verwenden
python3 live_monitor.py --file /pfad/zur/anderen.csv
```

## Voraussetzungen

### Python-Pakete

```bash
pip install pandas matplotlib
```

Oder:

```bash
pip install -r requirements.txt
```

### GUI-Backend (für Live-Monitor)

Für die Live-GUI wird zusätzlich ein grafisches Backend benötigt:

**Auf Debian/Ubuntu:**
```bash
sudo apt-get install python3-tk
```

**Auf Fedora/RHEL:**
```bash
sudo dnf install python3-tkinter
```

**Auf Arch Linux:**
```bash
sudo pacman -S tk
```

**Alternative:** Wenn tkinter nicht verfügbar ist, versucht das Skript automatisch andere Backends (Qt5, GTK3, WX).

## Hinweise

- Das GUI liest die CSV-Datei alle paar Sekunden neu
- Es werden nur die letzten N Stunden angezeigt (konfigurierbar)
- Das GUI läuft unabhängig vom Hauptskript
- Schließen Sie das GUI-Fenster zum Beenden
- Bei `--gui` wird das GUI automatisch mit dem Hauptskript beendet

### Wichtig: Grafische Umgebung erforderlich

Die GUI benötigt einen Desktop/X11-Server:
- ✓ Funktioniert auf Desktop-Systemen (Linux, macOS, Windows)
- ✓ Funktioniert mit X11-Forwarding: `ssh -X user@host`
- ✗ Funktioniert NICHT auf Servern ohne Display
- Alternative für Server: Verwenden Sie `plot_power_data.py`

### Kein Display verfügbar?

Wenn Sie die Meldung "No DISPLAY environment variable" sehen:

```bash
# Statt GUI: Erstellen Sie statische Plots
python3 plot_power_data.py
```

Das erstellt PNG-Dateien im `plots/` Ordner, die Sie herunterladen und ansehen können.

## Weitere Informationen

Siehe `POWER_LOGGING.md` für ausführliche Dokumentation.
