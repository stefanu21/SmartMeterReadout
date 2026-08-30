# CSV-Datei Reparatur

Wenn Sie bereits Daten mit dem alten Format (ohne Energie-Spalten) gesammelt haben und jetzt auf das neue Format umgestiegen sind, kann Ihre CSV-Datei gemischte Formate enthalten.

## Problem erkennen

Sie sehen diesen Fehler:
```
Error tokenizing data. C error: Expected 5 fields in line X, saw 7
```

Das bedeutet: Einige Zeilen haben das alte Format (5 Spalten), andere das neue (7 Spalten).

## Lösung: CSV-Datei reparieren

### Automatisch mit fix_csv.py

```bash
# Option 1: Neue reparierte Datei erstellen
python3 fix_csv.py power_data.csv --output power_data_fixed.csv

# Option 2: Original ersetzen (erstellt Backup)
python3 fix_csv.py power_data.csv --replace
```

Das Skript:
- Fügt fehlende Energie-Spalten zu alten Zeilen hinzu (mit Wert 0)
- Behält neue Zeilen unverändert
- Erstellt optional ein Backup

### Manuell

Wenn Sie die alte CSV-Datei manuell reparieren möchten:

1. **Backup erstellen:**
   ```bash
   cp power_data.csv power_data_backup.csv
   ```

2. **Alte Zeilen finden:**
   Zeilen ohne Energie-Daten haben nur 5 Werte:
   ```
   1788085657,2026-08-30 12:27:37,3421,0,3421
   ```

3. **Neue Spalten hinzufügen:**
   Fügen Sie `,0,0` am Ende hinzu:
   ```
   1788085657,2026-08-30 12:27:37,3421,0,3421,0,0
   ```

4. **Header aktualisieren:**
   Alter Header:
   ```
   timestamp,datetime,real_power_in,real_power_out,real_power_net
   ```
   
   Neuer Header:
   ```
   timestamp,datetime,real_power_in,real_power_out,real_power_net,real_energy_in,real_energy_out
   ```

## Alternative: Neu anfangen

Wenn Sie keine alten Daten behalten müssen:

```bash
# Alte Daten sichern
mv power_data.csv power_data_old.csv

# Neu starten (neue Datei wird automatisch erstellt)
python3 readout-smart-meter.py
```

## Nach der Reparatur

Die Plot-Skripte sollten jetzt funktionieren:

```bash
python3 plot_power_data.py --hours 24
```

## Hinweis

Die neuen Plot-Skripte (v4+) können auch gemischte Formate lesen, aber es ist besser, die Datei einmalig zu reparieren für bessere Performance.
