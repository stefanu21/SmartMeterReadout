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
- `real_energy_in`: Gesamt-Energiezähler Bezug in Wh
- `real_energy_out`: Gesamt-Energiezähler Einspeisung in Wh

## Verwendung

### 1. Datenerfassung starten

Das Smart Meter Readout Skript sammelt automatisch Daten und schreibt sie in `power_data.csv`:

```bash
python3 readout-smart-meter.py
```

Das Skript liest alle ~5 Sekunden die Daten vom Smart Meter und schreibt sie in die CSV-Datei.

**Beim Neustart**: Die Datei wird nicht überschrieben - neue Daten werden automatisch angehängt. Sie können das Programm beliebig oft stoppen und neu starten, ohne Daten zu verlieren.

#### Von vorne beginnen (alte Daten löschen)

Wenn Sie alte Daten entfernen und neu starten möchten:

```bash
# Löscht alte Daten und beginnt von vorne (erstellt Backup)
python3 readout-smart-meter.py --clear-data
```

Dies:
- Erstellt automatisch ein Backup als `power_data.csv.backup`
- Ersetzt die Datei mit einer neuen leeren Datei (mit Header)
- Alte Daten sind sicher im Backup gespeichert
- Die neue Datei existiert sofort (wichtig wenn --gui verwendet wird)

**Oder manuell:**
```bash
# Backup erstellen
mv power_data.csv power_data_backup.csv

# Neu starten (neue Datei wird automatisch erstellt)
python3 readout-smart-meter.py
```

#### Abtastrate anpassen

Standardmäßig wird jede Messung (~alle 5 Sekunden) geloggt. Sie können dies mit `--log-interval` anpassen:

```bash
# Jede Messung loggen (~5 Sekunden, Standard)
python3 readout-smart-meter.py --log-interval 1

# Jede 12. Messung loggen (~1 Minute)
python3 readout-smart-meter.py --log-interval 12

# Jede 60. Messung loggen (~5 Minuten)
python3 readout-smart-meter.py --log-interval 60

# Jede 120. Messung loggen (~10 Minuten)
python3 readout-smart-meter.py --log-interval 120
```

**Empfehlung:**
- Für detaillierte Analysen: `--log-interval 1` (Standard)
- Für Langzeit-Monitoring: `--log-interval 12` (1 Minute)
- Für Server mit begrenztem Speicher: `--log-interval 60` (5 Minuten)

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

- **power_overview_24h.png**: RealPower (Net), RealPowerIn und RealPowerOut in einer Grafik
- **energy_overview_24h.png**: RealEnergyIn und RealEnergyOut Zählerstände
- **daily_summary.png**: Tägliche Durchschnittswerte (ab 2 Tagen Daten)

Alle Grafiken werden im Ordner `plots/` gespeichert.

Sie können auch andere Zeiträume wählen:

```bash
# Letzte 6 Stunden
python3 plot_power_data.py --hours 6

# Letzte 2 Stunden
python3 plot_power_data.py --hours 2
```

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

# Abtastrate: Logge jede N-te Messung
LOGGING_INTERVAL = 1  # 1 = jede Messung (~5 sec)
                      # 12 = jede 12. Messung (~1 min)
                      # 60 = jede 60. Messung (~5 min)
```

Oder verwenden Sie Kommandozeilen-Parameter (überschreibt die Konfiguration):

```bash
python3 readout-smart-meter.py --log-interval 12
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

### Datenmenge und Speicherbedarf

- Das Skript sammelt standardmäßig etwa alle 5 Sekunden einen Datenpunkt
- Pro Tag werden ca. 17.280 Datenpunkte gesammelt (bei `--log-interval 1`)
- Die CSV-Datei wächst ca. 1-2 MB pro Tag

### Speicher sparen mit Abtastrate

Mit `--log-interval` können Sie die Datenmenge reduzieren:

| Interval | Abtastrate | Datenpunkte/Tag | Dateigröße/Tag |
|----------|-----------|-----------------|----------------|
| 1 | ~5 sec | 17.280 | ~1.5 MB |
| 12 | ~1 min | 1.440 | ~130 KB |
| 60 | ~5 min | 288 | ~26 KB |
| 120 | ~10 min | 144 | ~13 KB |

### Daten archivieren

Für längere Zeiträume können Sie ältere Daten archivieren:

```bash
# Monatliches Backup
cp power_data.csv power_data_$(date +%Y%m).csv

# Alte Daten löschen (Optional - Achtung: Datenverlust!)
# > power_data.csv  # Leert die Datei
```

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
