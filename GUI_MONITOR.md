# Smart Meter Live GUI Monitor

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
# Zeige letzte 30 Minuten
python3 readout-smart-meter.py --gui --gui-hours 0.5

# Zeige letzte 6 Stunden
python3 live_monitor.py --hours 6

# Schnellere Updates (alle 2 Sekunden)
python3 live_monitor.py --interval 2000

# Eigene Datendatei verwenden
python3 live_monitor.py --file /pfad/zur/anderen.csv
```

## Voraussetzungen

```bash
pip install pandas matplotlib
```

Oder:

```bash
pip install -r requirements.txt
```

## Hinweise

- Das GUI liest die CSV-Datei alle paar Sekunden neu
- Es werden nur die letzten N Stunden angezeigt (konfigurierbar)
- Das GUI läuft unabhängig vom Hauptskript
- Schließen Sie das GUI-Fenster zum Beenden
- Bei `--gui` wird das GUI automatisch mit dem Hauptskript beendet

## Weitere Informationen

Siehe `POWER_LOGGING.md` für ausführliche Dokumentation.
