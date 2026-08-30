# Power Data Logging und Visualisierung

## Übersicht

Das Smart Meter Readout Skript wurde erweitert, um die Stromverbrauchsdaten automatisch in eine CSV-Datei zu schreiben. Diese Daten können dann zur Erstellung von Grafiken verwendet werden.

**Wichtig**: Die CSV-Datei wird beim Neustart des Programms **nicht überschrieben**. Neue Daten werden immer an die bestehende Datei angehängt, sodass Sie einen kontinuierlichen Verlauf über mehrere Programmstarts hinweg haben.

## Neue Dateien

- **power_data.csv**: CSV-Datei mit Zeitstempel und Leistungsdaten (wird automatisch erstellt)
- **live_monitor.py**: Python-Skript für Live-Überwachung in einem GUI-Fenster
- **plot_power_data.py**: Python-Skript zur Visualisierung der gesammelten Daten (erstellt PNG-Dateien)

## Datenformat

Die CSV-Datei `power_data.csv` enthält folgende Spalten:

- `timestamp`: Unix-Timestamp (Sekunden seit 1970)
- `datetime`: Lesbare Zeitangabe (YYYY-MM-DD HH:MM:SS)
- `real_power_in`: Bezogene Leistung in Watt (vom Netz)
- `real_power_out`: Eingespeiste Leistung in Watt (ins Netz)
- `real_power_net`: Netto-Leistung in Watt (Bezug - Einspeisung)

## Verwendung

### 1. Datenerfassung starten

Das Smart Meter Readout Skript sammelt automatisch Daten und schreibt sie in `power_data.csv`:

```bash
python3 readout-smart-meter.py
```

Das Skript liest alle ~5 Sekunden die Daten vom Smart Meter und schreibt sie in die CSV-Datei.

**Beim Neustart**: Die Datei wird nicht überschrieben - neue Daten werden automatisch angehängt. Sie können das Programm beliebig oft stoppen und neu starten, ohne Daten zu verlieren.

### 1a. Mit Live-GUI Monitor (optional)

Um die Daten in Echtzeit in einem grafischen Fenster zu sehen, starten Sie das Skript mit der `--gui` Option:

```bash
python3 readout-smart-meter.py --gui
```

Weitere GUI-Optionen:

```bash
# Zeige die letzten 2 Stunden im GUI
python3 readout-smart-meter.py --gui --gui-hours 2

# Zeige die letzten 30 Minuten
python3 readout-smart-meter.py --gui --gui-hours 0.5
```

Das GUI-Fenster zeigt:
- **Oberer Graph**: Netto-Leistung (Net Power) in Echtzeit
- **Unterer Graph**: Bezug (rot) und Einspeisung (grün) getrennt
- **Statuszeile**: Aktuelle Werte, Durchschnitt, Maximum, Minimum

Das GUI aktualisiert sich automatisch alle 5 Sekunden und zeigt immer die neuesten Daten an.

### 1b. GUI separat starten

Sie können den Live-Monitor auch unabhängig vom Hauptskript starten:

```bash
# Standard: Zeigt letzte Stunde
python3 live_monitor.py

# Zeige letzte 3 Stunden
python3 live_monitor.py --hours 3

# Schnellere Updates (alle 2 Sekunden)
python3 live_monitor.py --hours 1 --interval 2000
```

### 2. Datenerfassung deaktivieren

Falls Sie die Datenerfassung deaktivieren möchten, ändern Sie in `readout-smart-meter.py`:

```python
ENABLE_DATA_LOGGING = False
```

### 3. Statische Grafiken erstellen (PNG-Dateien)

Um Grafiken aus den gesammelten Daten zu erstellen:

```bash
python3 plot_power_data.py
```

Das Skript erstellt folgende Visualisierungen:

- **power_last_24h.png**: Netto-Stromverbrauch der letzten 24 Stunden
- **power_in_out_last_24h.png**: Getrennte Darstellung von Bezug und Einspeisung
- **daily_summary.png**: Tägliche Durchschnittswerte (ab 2 Tagen Daten)

Alle Grafiken werden im Ordner `plots/` gespeichert.

### 4. Dependencies installieren

Für die Visualisierung werden zusätzliche Pakete benötigt:

```bash
pip install pandas matplotlib
```

Oder alle Dependencies auf einmal:

```bash
pip install -r requirements.txt
```

## Konfiguration

In `readout-smart-meter.py` können Sie folgende Einstellungen anpassen:

```python
# Pfad zur Daten-Datei
DATA_FILE = os.path.realpath(os.path.join(os.path.dirname(__file__), "power_data.csv"))

# Datenerfassung aktivieren/deaktivieren
ENABLE_DATA_LOGGING = True
```

## Beispielausgabe

Das Skript zeigt während der Ausführung Statistiken an:

```
Smart Meter Power Data Visualization
============================================================
Loading data from: /path/to/power_data.csv
Loaded 17280 data points
Time range: 2026-08-29 10:00:00 to 2026-08-30 10:00:00

============================================================
Power Statistics - Last 24 Hours
============================================================
Time range: 2026-08-29 10:00:00 to 2026-08-30 10:00:00
Number of measurements: 17280

Net Power (real_power_net):
  Average: 542.3 W
  Maximum: 2850.0 W
  Minimum: -3200.0 W

Power Consumption (real_power_in):
  Average: 1250.5 W
  Maximum: 3500.0 W

Power Feed-in (real_power_out):
  Average: 708.2 W
  Maximum: 4800.0 W
============================================================
```

## Tipps

- Das Skript sammelt etwa alle 5 Sekunden einen Datenpunkt
- Pro Tag werden ca. 17.280 Datenpunkte gesammelt
- Die CSV-Datei wächst ca. 1-2 MB pro Tag
- Für längere Zeiträume können Sie ältere Daten archivieren oder löschen

## Eigene Grafiken erstellen

Sie können die CSV-Datei auch mit anderen Tools verwenden:

- **Excel/LibreOffice**: Direkt als CSV importieren
- **Python/Pandas**: Eigene Analysen durchführen
- **Grafana**: Für Echtzeit-Dashboards (erfordert zusätzliches Setup)

Beispiel für eigene Python-Analyse:

```python
import pandas as pd

# Daten laden
df = pd.read_csv('power_data.csv')
df['datetime'] = pd.to_datetime(df['datetime'])

# Stündlicher Durchschnitt
df['hour'] = df['datetime'].dt.hour
hourly_avg = df.groupby('hour')['real_power_net'].mean()

print(hourly_avg)
```
