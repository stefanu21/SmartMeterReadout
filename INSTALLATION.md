# Installation und Setup

## Virtual Environment

**WICHTIG:** Dieses Projekt ist selbst ein Virtual Environment!

Das gesamte Verzeichnis `/home/sursella/playground/SmartMeterReadout` ist ein Python Virtual Environment.
Das bedeutet, dass alle Python-Pakete lokal in diesem Verzeichnis installiert sind.

### Virtual Environment aktivieren

**Vor jeder Verwendung** müssen Sie das Virtual Environment aktivieren:

```bash
cd /home/sursella/playground/SmartMeterReadout
source bin/activate
```

Nach der Aktivierung sehen Sie `(SmartMeterReadout)` vor Ihrem Terminal-Prompt:
```
(SmartMeterReadout) user@host:~/playground/SmartMeterReadout$
```

### Virtual Environment deaktivieren

```bash
deactivate
```

## Pakete installieren

### Alle Pakete auf einmal

Mit aktiviertem Virtual Environment:

```bash
source bin/activate
pip install -r requirements.txt
```

### Einzelne Pakete

```bash
source bin/activate

# Hauptpakete
pip install beautifulsoup4 cryptography gurux_dlms pyserial lxml charset-normalizer

# Visualisierung
pip install pandas matplotlib

# Optional: Interaktive Cursor-Tooltips
pip install mplcursors
```

### Ohne Virtual Environment Aktivierung

Sie können auch direkt den Python-Interpreter aus dem venv verwenden:

```bash
./bin/pip install -r requirements.txt
```

## System-Pakete (optional)

Für die Live-GUI wird ein grafisches Backend benötigt:

### Debian/Ubuntu
```bash
sudo apt-get install python3-tk
```

### Fedora/RHEL
```bash
sudo dnf install python3-tkinter
```

### Arch Linux
```bash
sudo pacman -S tk
```

Details siehe `SYSTEM_DEPENDENCIES.md`.

## Pakete überprüfen

### Alle installierten Pakete anzeigen

```bash
source bin/activate
pip list
```

Oder ohne Aktivierung:
```bash
./bin/pip list
```

### Visualisierungspakete testen

```bash
source bin/activate
python3 -c "
import pandas; print('✓ pandas:', pandas.__version__)
import matplotlib; print('✓ matplotlib:', matplotlib.__version__)
import mplcursors; print('✓ mplcursors:', mplcursors.__version__)
"
```

## Scripts ausführen

### Option 1: Mit aktiviertem Virtual Environment (empfohlen)

```bash
source bin/activate
python3 readout-smart-meter.py
python3 plot_power_data.py
python3 live_monitor.py
```

### Option 2: Ohne Aktivierung

```bash
./bin/python3 readout-smart-meter.py
./bin/python3 plot_power_data.py
./bin/python3 live_monitor.py
```

### Option 3: Shebang in Scripts

Die Scripts haben einen Shebang (`#!/usr/bin/env python3`), aber dieser verwendet das System-Python.
Für das Virtual Environment müssen Sie entweder:
- Das venv aktivieren (Option 1), oder
- Explizit `./bin/python3` verwenden (Option 2)

## Häufige Probleme

### "ModuleNotFoundError: No module named 'pandas'"

**Problem:** Sie verwenden das System-Python statt das Virtual Environment.

**Lösung:**
```bash
# Entweder venv aktivieren:
source bin/activate
python3 script.py

# Oder direkt venv-Python verwenden:
./bin/python3 script.py
```

### "ModuleNotFoundError: No module named 'mplcursors'"

**Problem:** `mplcursors` ist nicht installiert (optional für Cursor-Tooltips).

**Lösung:**
```bash
source bin/activate
pip install mplcursors
```

Die Scripts funktionieren auch ohne `mplcursors`, nur ohne die Hover-Tooltips.

### "No DISPLAY environment variable"

**Problem:** Sie versuchen die GUI auf einem Server ohne Display zu starten.

**Lösung:** Verwenden Sie stattdessen statische Plots:
```bash
source bin/activate
python3 plot_power_data.py
```

Siehe `SERVER_USAGE.md` für Details.

## Service Installation

Wenn Sie das Script als systemd Service laufen lassen, müssen Sie den venv-Python-Pfad verwenden:

**In `readout-smart-meter.service`:**
```ini
[Service]
ExecStart=/home/sursella/playground/SmartMeterReadout/bin/python3 /home/sursella/playground/SmartMeterReadout/readout-smart-meter.py
```

**NICHT:**
```ini
ExecStart=/usr/bin/python3 /home/sursella/playground/SmartMeterReadout/readout-smart-meter.py
```

## Warum Virtual Environment?

- ✓ Keine Konflikte mit System-Paketen
- ✓ Einfache Verwaltung von Abhängigkeiten
- ✓ Verschiedene Python-Versionen möglich
- ✓ Saubere Trennung pro Projekt

## Weitere Informationen

- **GUI:** Siehe `GUI_MONITOR.md`
- **Plots:** Siehe `POWER_LOGGING.md`
- **CLI:** Siehe `CLI_PARAMETERS.md`
- **Server:** Siehe `SERVER_USAGE.md`
