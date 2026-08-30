# Kommandozeilen-Parameter - Übersicht

## readout-smart-meter.py

Hauptskript zum Auslesen des Smart Meters und Datenerfassung.

### Grundlegende Parameter

| Parameter | Beschreibung | Standard | Beispiel |
|-----------|-------------|----------|----------|
| `--port PORT` | Serieller Port | `/dev/ttyUSB0` | `--port /dev/ttyUSB1` |
| `--key KEY` | AES-Entschlüsselungsschlüssel | Aus Config | `--key 48E2C...` |

### Datenerfassung

| Parameter | Beschreibung | Standard | Beispiel |
|-----------|-------------|----------|----------|
| `--log-interval N` | Logge jede N-te Messung | 1 (~5 sec) | `--log-interval 12` (1 min) |
| `--clear-data` | Löscht alte Daten, startet neu (mit Backup) | - | `--clear-data` |

**Abtastrate-Beispiele:**
- `--log-interval 1` → ~5 Sekunden (720 Einträge/Stunde)
- `--log-interval 12` → ~1 Minute (60 Einträge/Stunde)
- `--log-interval 60` → ~5 Minuten (12 Einträge/Stunde)
- `--log-interval 120` → ~10 Minuten (6 Einträge/Stunde)

### GUI-Optionen

| Parameter | Beschreibung | Standard | Beispiel |
|-----------|-------------|----------|----------|
| `--gui` | Startet Live-GUI automatisch | Aus | `--gui` |
| `--gui-hours N` | Zeitfenster im GUI (Stunden) | 1 | `--gui-hours 2` |

**Hinweis:** GUI benötigt grafische Umgebung (Desktop/X11)

### Beispiele

```bash
# Standard: Daten alle 5 Sekunden
python3 readout-smart-meter.py

# Neu anfangen (alte Daten löschen)
python3 readout-smart-meter.py --clear-data

# Jede Minute loggen
python3 readout-smart-meter.py --log-interval 12

# Mit Live-GUI, letzte 2 Stunden anzeigen
python3 readout-smart-meter.py --gui --gui-hours 2

# Alle 5 Minuten loggen, mit GUI
python3 readout-smart-meter.py --log-interval 60 --gui

# Anderer Port mit eigenem Schlüssel
python3 readout-smart-meter.py --port /dev/ttyUSB1 --key 48E2C...

# Komplett: Neu starten, 1-min Intervall, GUI
python3 readout-smart-meter.py --clear-data --log-interval 12 --gui --gui-hours 3
```

---

## plot_power_data.py

Erstellt statische PNG-Grafiken aus gesammelten Daten.

### Parameter

| Parameter | Beschreibung | Standard | Beispiel |
|-----------|-------------|----------|----------|
| `--hours N` | Zeitraum in Stunden | 24 | `--hours 6` |
| `--file FILE` | CSV-Datei | `power_data.csv` | `--file data.csv` |
| `--interactive` oder `-i` | Interaktive Ansicht statt PNG | Aus | `-i` |

### Beispiele

```bash
# Standard: Letzte 24 Stunden (PNG-Dateien)
python3 plot_power_data.py

# Letzte 6 Stunden
python3 plot_power_data.py --hours 6

# Interaktive Ansicht mit Zoom/Pan
python3 plot_power_data.py --hours 6 --interactive

# Kurz: Interaktiv
python3 plot_power_data.py -i

# Andere Datendatei
python3 plot_power_data.py --file power_data_2024.csv
```

**Erzeugte Grafiken:**
- `plots/power_overview_Xh.png` - RealPower, RealPowerIn, RealPowerOut
- `plots/energy_overview_Xh.png` - RealEnergyIn, RealEnergyOut
- `plots/daily_summary.png` - Tägliche Durchschnitte (ab 2 Tagen)

---

## live_monitor.py

Live-GUI für Echtzeit-Überwachung (benötigt Desktop/X11).

### Parameter

| Parameter | Beschreibung | Standard | Beispiel |
|-----------|-------------|----------|----------|
| `--hours N` | Zeitfenster in Stunden | 1 | `--hours 3` |
| `--interval MS` | Update-Intervall (Millisekunden) | 5000 | `--interval 2000` |
| `--file FILE` | CSV-Datei | `power_data.csv` | `--file data.csv` |

### Beispiele

```bash
# Standard: Letzte Stunde, Update alle 5 Sekunden
python3 live_monitor.py

# Letzte 3 Stunden
python3 live_monitor.py --hours 3

# Schnellere Updates (alle 2 Sekunden)
python3 live_monitor.py --interval 2000

# Letzte 30 Minuten, schnelle Updates
python3 live_monitor.py --hours 0.5 --interval 2000

# Andere Datendatei
python3 live_monitor.py --file backup_data.csv
```

**Interaktive Steuerung:**
- Mausrad: Y-Achse scrollen
- Shift+Mausrad: Y-Achse zoomen
- Ctrl+Mausrad: X-Achse (Zeit) zoomen
- Toolbar: Pan, Zoom, Home Buttons

---

## fix_csv.py

Repariert CSV-Dateien mit gemischten Formaten.

### Parameter

| Parameter | Beschreibung | Standard | Beispiel |
|-----------|-------------|----------|----------|
| `input` | Eingabe-CSV | `power_data.csv` | `old_data.csv` |
| `--output FILE` | Ausgabe-Datei | `input.fixed` | `--output fixed.csv` |
| `--replace` | Ersetzt Original (mit Backup) | - | `--replace` |

### Beispiele

```bash
# Reparieren in neue Datei
python3 fix_csv.py power_data.csv

# Original ersetzen (mit Backup)
python3 fix_csv.py power_data.csv --replace

# Eigene Ausgabe-Datei
python3 fix_csv.py old_data.csv --output repaired.csv
```

---

## Häufige Kombinationen

### Produktiv-Betrieb (Server)
```bash
# Optimiert für Langzeit-Monitoring
python3 readout-smart-meter.py --log-interval 12
```

### Analyse-Modus (Desktop)
```bash
# Detaillierte Daten mit Live-Überwachung
python3 readout-smart-meter.py --gui --gui-hours 2
```

### Speicher-sparsam (IoT/Embedded)
```bash
# Nur alle 5 Minuten loggen
python3 readout-smart-meter.py --log-interval 60
```

### Neustart mit Bereinigung
```bash
# Alte Daten entfernen, mit GUI neu starten
python3 readout-smart-meter.py --clear-data --gui --log-interval 12
```
