# Cursor Test Anleitung

## Problem: "Ich sehe keinen Cursor"

Der Cursor funktioniert nur, wenn:
1. ✓ Virtual Environment aktiviert ist
2. ✓ mplcursors installiert ist
3. ✓ Ein GUI-Display verfügbar ist (kein SSH ohne X11)

## Schritt-für-Schritt Test

### 1. Virtual Environment aktivieren

```bash
cd /home/sursella/playground/SmartMeterReadout
source bin/activate
```

Sie sollten jetzt `(SmartMeterReadout)` im Prompt sehen.

### 2. Prüfen ob mplcursors installiert ist

```bash
python3 -c "import mplcursors; print('✓ mplcursors:', mplcursors.__version__)"
```

Erwartete Ausgabe: `✓ mplcursors: 0.7.1`

Falls Fehler: `pip install mplcursors`

### 3. Einfacher Cursor-Test

```bash
python3 test_cursor_simple.py
```

**Was passieren sollte:**
- Ein Fenster mit 2 farbigen Kurven öffnet sich
- Wenn Sie mit der Maus über die Linien fahren, erscheint ein **gelber Tooltip**
- Der Tooltip zeigt X und Y Werte an
- Der Tooltip "springt" zum nächsten Datenpunkt

**Falls kein Fenster erscheint:**
- Läuft das System ohne Display? (Server/SSH)
- Lösung: Verwenden Sie `ssh -X` für X11-Forwarding oder nur statische Plots

### 4. Test mit echten Power-Daten

```bash
# Interaktive statische Plots:
python3 plot_power_data.py --interactive --hours 2

# Oder Live-GUI:
python3 live_monitor.py --hours 1
```

**Was passieren sollte:**
- Plot-Fenster öffnet sich
- Beim Überfahren der Power-Kurven (blau/rot/grün) erscheint ein **weißer Tooltip**
- Der Tooltip zeigt: **Zeit (HH:MM:SS)** und **Leistung (xxx.x W)**
- Der Tooltip zeigt nur tatsächliche Messwerte (nicht interpoliert)

## Häufige Probleme

### "ModuleNotFoundError: No module named 'mplcursors'"

**Ursache:** Virtual Environment nicht aktiviert ODER mplcursors nicht installiert

**Lösung:**
```bash
source bin/activate
pip install mplcursors
```

### "No DISPLAY environment variable"

**Ursache:** Kein X11-Display verfügbar (Headless Server/SSH)

**Lösung 1:** X11-Forwarding nutzen
```bash
# Auf Ihrem lokalen Computer:
ssh -X user@server
```

**Lösung 2:** Nur statische PNG-Plots verwenden
```bash
python3 plot_power_data.py --hours 2
# Dann die PNG-Dateien aus plots/ herunterladen
```

### "Fenster öffnet sich, aber kein Cursor sichtbar"

**Mögliche Ursachen:**
1. **Maus bewegt sich nicht über die Linien**
   - Lösung: Bewegen Sie die Maus direkt über die farbigen Kurven
   
2. **Backend-Problem**
   - Test mit einfachem Script: `python3 test_cursor_simple.py`
   - Falls das funktioniert, ist es ein anderes Problem
   
3. **mplcursors-Version zu alt**
   - Update: `pip install --upgrade mplcursors`

### Tooltip erscheint nur manchmal

**Normal!** Der Cursor verwendet `hover=2` (Transient mode).
Das bedeutet:
- Tooltip erscheint nur beim Hover **nahe** der Linie
- Tooltip verschwindet wenn Sie die Maus wegbewegen
- Das ist beabsichtigt, um nicht im Weg zu sein

## Debugging

### Vollständiger System-Check

```bash
cd /home/sursella/playground/SmartMeterReadout
source bin/activate

echo "=== Python ==="
which python3
python3 --version

echo "=== Pakete ==="
pip list | grep -E "(matplotlib|pandas|mplcursors|numpy)"

echo "=== Display ==="
echo $DISPLAY

echo "=== Test Import ==="
python3 -c "
import matplotlib
import matplotlib.pyplot as plt
import pandas
import numpy
import mplcursors
print('✓ All imports successful')
print('mplcursors version:', mplcursors.__version__)
"
```

### Test ohne GUI

Falls Sie keinen Display haben, können Sie testen ob der Code funktioniert:

```bash
python3 -c "
import matplotlib
matplotlib.use('Agg')  # Non-GUI backend
import matplotlib.pyplot as plt
import mplcursors

fig, ax = plt.subplots()
line = ax.plot([1,2,3], [1,2,3])
cursor = mplcursors.cursor(line, hover=2)
print('✓ Cursor can be created (but not shown without display)')
"
```

## Kontakt

Falls der Cursor immer noch nicht funktioniert, teilen Sie bitte die Ausgabe von:

```bash
cd /home/sursella/playground/SmartMeterReadout
source bin/activate
python3 test_cursor_simple.py 2>&1 | tee cursor_debug.log
```

Und senden Sie `cursor_debug.log`.
