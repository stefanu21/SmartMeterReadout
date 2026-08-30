# Server/Headless Betrieb (ohne GUI)

Wenn Sie das Smart Meter Readout auf einem Server oder System ohne grafische Oberfläche betreiben, verwenden Sie diese Anleitung.

## Datenerfassung starten

```bash
# Starten ohne GUI (Standard)
python3 readout-smart-meter.py

# Im Hintergrund laufen lassen
nohup python3 readout-smart-meter.py > /dev/null 2>&1 &

# Oder als systemd Service (siehe readout-smart-meter.service)
sudo systemctl start readout-smart-meter
```

## Daten visualisieren

Da die Live-GUI ein Display benötigt, verwenden Sie stattdessen statische Plots:

```bash
# Grafiken erstellen
python3 plot_power_data.py
```

Dies erstellt PNG-Dateien im `plots/` Ordner:
- `power_last_24h.png` - Netto-Leistung der letzten 24h
- `power_in_out_last_24h.png` - Bezug und Einspeisung getrennt
- `daily_summary.png` - Tägliche Durchschnitte

## Grafiken vom Server holen

### Mit SCP:
```bash
# Auf Ihrem lokalen Rechner:
scp user@server:/pfad/zu/SmartMeterReadout/plots/*.png ./
```

### Mit SFTP:
```bash
sftp user@server
cd /pfad/zu/SmartMeterReadout/plots
mget *.png
exit
```

### Mit Webserver (optional):
```bash
# Auf dem Server:
cd /pfad/zu/SmartMeterReadout
python3 -m http.server 8000

# Dann im Browser öffnen:
# http://server-ip:8000/plots/
```

## Daten analysieren

Sie können die CSV-Datei auch herunterladen und lokal analysieren:

```bash
# CSV herunterladen
scp user@server:/pfad/zu/SmartMeterReadout/power_data.csv ./

# Auf lokalem Rechner mit GUI:
python3 live_monitor.py --file power_data.csv --hours 24
```

## Automatische Plot-Erstellung

Erstellen Sie einen Cronjob für regelmäßige Plot-Updates:

```bash
# Crontab bearbeiten
crontab -e

# Plots jede Stunde aktualisieren
0 * * * * cd /pfad/zu/SmartMeterReadout && python3 plot_power_data.py

# Plots alle 15 Minuten aktualisieren
*/15 * * * * cd /pfad/zu/SmartMeterReadout && python3 plot_power_data.py
```

## Daten-Backup

```bash
# Tägliches Backup der CSV-Datei
0 2 * * * cp /pfad/zu/SmartMeterReadout/power_data.csv /backup/power_data_$(date +\%Y\%m\%d).csv
```

## Troubleshooting

### "No module named 'tkinter'" Fehler

Dieser Fehler erscheint, wenn Sie versuchen `--gui` zu verwenden:
- Lösung: Verwenden Sie `plot_power_data.py` statt der Live-GUI
- Oder: Installieren Sie tkinter: `sudo apt-get install python3-tk` (nur auf Desktop-Systemen sinnvoll)

### "No DISPLAY environment variable"

Dies ist normal auf Servern:
- Verwenden Sie die GUI **nicht** mit `--gui`
- Nutzen Sie stattdessen `plot_power_data.py`

### Plots ansehen ohne Download

Richten Sie einen einfachen Webserver ein:
```bash
# In der SmartMeterReadout-Verzeichnis:
python3 -m http.server 8000 --bind 0.0.0.0

# Dann im Browser: http://SERVER-IP:8000/plots/
```

## Weitere Informationen

- Ausführliche Dokumentation: `POWER_LOGGING.md`
- GUI-Dokumentation (für Desktop): `GUI_MONITOR.md`
