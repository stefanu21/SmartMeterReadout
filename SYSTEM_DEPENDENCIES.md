# System Dependencies

Diese Abhängigkeiten müssen über den System-Paketmanager installiert werden, **nicht** über pip.

## Für Live-GUI Monitor (optional)

Nur erforderlich, wenn Sie `--gui` oder `live_monitor.py` verwenden möchten.

### Debian/Ubuntu
```bash
sudo apt-get install python3-tk
```

### Fedora/RHEL/CentOS
```bash
sudo dnf install python3-tkinter
```

### Arch Linux
```bash
sudo pacman -S tk
```

### macOS
Tkinter ist normalerweise bereits in Python enthalten.

### Windows
Tkinter ist normalerweise bereits in Python enthalten.

## Alternative: GUI ohne tkinter

Das `live_monitor.py` Skript versucht automatisch verschiedene Backends:
1. TkAgg (bevorzugt)
2. Qt5Agg
3. GTK3Agg
4. WXAgg

Wenn Sie Qt5 bevorzugen:
```bash
# Debian/Ubuntu
sudo apt-get install python3-pyqt5

# Oder über pip
pip install PyQt5
```

## Interaktive Cursor (optional)

Für interaktive Tooltip-Cursor beim Überfahren der Power-Kurven:
```bash
pip install mplcursors
```

**Hinweis:** Dies ist optional. Wenn `mplcursors` nicht installiert ist, funktionieren die Plots
weiterhin normal, aber ohne die Hover-Tooltips die Zeit und Watt-Werte anzeigen.

## Für Server ohne GUI

Wenn Sie das System auf einem Server ohne Display betreiben:
- **tkinter wird NICHT benötigt**
- Verwenden Sie `plot_power_data.py` statt `live_monitor.py`
- Siehe `SERVER_USAGE.md` für Details

## Installation überprüfen

```bash
# Prüfen ob tkinter verfügbar ist:
python3 -c "import tkinter; print('tkinter OK')"

# Prüfen ob mplcursors verfügbar ist:
python3 -c "import mplcursors; print('mplcursors OK')"

# Wenn Fehler: Paket nicht installiert
# Wenn "... OK": Paket ist verfügbar
```

## Warum nicht in requirements.txt?

`tkinter` ist ein **System-Paket**, das Teil der Python-Installation ist.
Es kann nicht über pip installiert werden und muss vom System-Paketmanager
installiert werden. Daher ist es nicht in `requirements.txt` enthalten.
