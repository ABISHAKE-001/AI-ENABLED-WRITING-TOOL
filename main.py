"""
Voice-to-G-code Writing Machine
================================
Pipeline: microphone -> offline speech-to-text (Vosk) -> on-screen preview
-> confirm/re-record -> block-letter G-code file for a pen plotter.

USAGE
-----
Normal (voice) mode:
    python voice_to_gcode.py

Test mode - skip the microphone and convert text directly (useful while
you're still setting up the mic/model, or for a quick sanity check):
    python voice_to_gcode.py --text "Hello from the writing machine"

Save a PNG preview of the pen path alongside the .gcode file:
    python voice_to_gcode.py --text "Hello" --preview

See the "SETUP" section at the bottom of this file for the one-time
install steps (pip packages + Vosk model download).
"""

import os
import sys
import json
import queue
import argparse
import datetime
import threading

# ---------------------------------------------------------------- CONFIG --
# Resolve paths relative to this script's own location, not the terminal's
# current directory - otherwise running it from VS Code, a shortcut, or a
# different folder than the one you cd'd into will fail to find "model"
# even when it's sitting right next to the script.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "model")   # folder holding the unzipped Vosk model
SAMPLE_RATE = 16000                            # Vosk expects 16 kHz mono audio

OUTPUT_DIR = os.path.join(BASE_DIR, "gcode_output")

FONT_SIZE_MM = 10           # letter height, in mm
LINE_HEIGHT_MM = 14         # baseline-to-baseline spacing between lines
PAGE_WIDTH_MM = 190         # usable writing width  (A4 width  210 - 2x10 margin)
PAGE_HEIGHT_MM = 277        # usable writing height (A4 height 297 - 2x10 margin)
MARGIN_X = 10
MARGIN_Y = 10

FEED_DRAW = 800             # mm/min while the pen is down and drawing
FEED_MOVE = 3000            # mm/min for travel moves / pen lift-lower
PEN_UP_Z = 5.0               # Z height, pen lifted off the paper
PEN_DOWN_Z = 0.0             # Z height, pen touching the paper
# NOTE: if your pen is on a servo wired to the spindle output instead of a
# real Z axis, swap the two "G1 Z.. F.." lines in text_to_gcode() for
# "M5" (pen up) / "M3 S1000" (pen down) - GRBL's laser/servo trick.
# ----------------------------------------------------------------------- #


# ===========================================================================
# STEP 1 - Voice capture + offline transcription (Vosk)
# ===========================================================================
def record_and_transcribe():
    """Record from the default mic until Enter is pressed, return the text."""
    from vosk import Model, KaldiRecognizer
    import sounddevice as sd

    if not os.path.isdir(MODEL_PATH):
        sys.exit(
            f"Vosk model folder '{MODEL_PATH}' not found.\n"
            "Download it first - see the SETUP notes at the bottom of this file."
        )

    model = Model(MODEL_PATH)
    rec = KaldiRecognizer(model, SAMPLE_RATE)
    audio_q = queue.Queue()

    def audio_callback(indata, frames, time_info, status):
        audio_q.put(bytes(indata))

    print("\nPress Enter to start recording, speak your sentence, "
          "then press Enter again to stop.")
    input()
    print("Listening... (press Enter to stop)")

    stop_flag = {"stop": False}

    def wait_for_enter():
        input()
        stop_flag["stop"] = True

    threading.Thread(target=wait_for_enter, daemon=True).start()

    with sd.RawInputStream(samplerate=SAMPLE_RATE, blocksize=8000,
                            dtype="int16", channels=1,
                            callback=audio_callback):
        while not stop_flag["stop"]:
            data = audio_q.get()
            rec.AcceptWaveform(data)

    result = json.loads(rec.FinalResult())
    return result.get("text", "").strip()


def get_confirmed_text():
    """Record -> show transcript -> confirm / re-record / type-manually loop."""
    while True:
        text = record_and_transcribe()
        print(f'\nRecognized: "{text}"')
        choice = input("Use this? [y]es / [r]e-record / [t]ype instead: ").strip().lower()
        if choice == "y" and text:
            return text
        if choice == "t":
            typed = input("Type the sentence to write: ").strip()
            if typed:
                return typed
        # anything else -> loop back and record again


# ===========================================================================
# STEP 2 - Text -> G-code (block-letter outline tracing)
# ===========================================================================
# Uses matplotlib's font engine to turn each line of text into vector
# outlines (built-in monospace font, no extra downloads needed), then walks
# those outlines as pen-down strokes with pen-up travel moves in between -
# this is what naturally handles the "holes" in letters like O, A, e, etc.
def wrap_text(text, max_width_mm, font_size_mm, font_prop):
    from matplotlib.textpath import TextPath

    words = text.split()
    if not words:
        return []
    lines, current = [], ""
    for w in words:
        trial = (current + " " + w).strip()
        width = TextPath((0, 0), trial, size=font_size_mm, prop=font_prop).get_extents().width
        if width <= max_width_mm or not current:
            current = trial
        else:
            lines.append(current)
            current = w
    lines.append(current)
    return lines


def text_to_gcode(text, preview_path=None):
    from matplotlib.textpath import TextPath
    from matplotlib.font_manager import FontProperties

    font_prop = FontProperties(family="monospace")
    max_width = PAGE_WIDTH_MM - 2 * MARGIN_X
    lines = wrap_text(text, max_width, FONT_SIZE_MM, font_prop)

    gcode = [
        "; Auto-generated by voice_to_gcode.py",
        f"; Text: {text}",
        "G21 ; millimeters",
        "G90 ; absolute positioning",
        f"G1 Z{PEN_UP_Z} F{FEED_MOVE} ; pen up",
    ]
    strokes_for_preview = []

    for line_idx, line in enumerate(lines):
        if not line.strip():
            continue
        tp = TextPath((0, 0), line, size=FONT_SIZE_MM, prop=font_prop)
        row_y = PAGE_HEIGHT_MM - MARGIN_Y - FONT_SIZE_MM - line_idx * LINE_HEIGHT_MM
        if row_y < MARGIN_Y:
            print(f"Warning: line {line_idx + 1} falls off the page and was skipped "
                  f"({len(lines)} lines don't fit on one sheet).")
            continue

        for poly in tp.to_polygons():
            if len(poly) < 2:
                continue
            x0, y0 = poly[0]
            X0, Y0 = x0 + MARGIN_X, row_y + y0
            gcode.append(f"G1 Z{PEN_UP_Z} F{FEED_MOVE}")
            gcode.append(f"G0 X{X0:.3f} Y{Y0:.3f}")
            gcode.append(f"G1 Z{PEN_DOWN_Z} F{FEED_MOVE}")
            pts = [(X0, Y0)]
            for (x, y) in poly[1:]:
                X, Y = x + MARGIN_X, row_y + y
                gcode.append(f"G1 X{X:.3f} Y{Y:.3f} F{FEED_DRAW}")
                pts.append((X, Y))
            strokes_for_preview.append(pts)

    gcode.append(f"G1 Z{PEN_UP_Z} F{FEED_MOVE} ; pen up")
    gcode.append("G0 X0 Y0 ; return home")
    gcode.append("M2 ; program end")

    if preview_path:
        _save_preview(strokes_for_preview, preview_path)

    return "\n".join(gcode)


def _save_preview(strokes, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8, 8 * PAGE_HEIGHT_MM / PAGE_WIDTH_MM))
    for pts in strokes:
        xs, ys = zip(*pts)
        ax.plot(xs, ys, "k-", linewidth=1)
    ax.set_xlim(0, PAGE_WIDTH_MM + 2 * MARGIN_X)
    ax.set_ylim(0, PAGE_HEIGHT_MM + MARGIN_Y)
    ax.set_aspect("equal")
    ax.set_title("Pen path preview")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"Preview image saved to: {path}")


# ===========================================================================
# MAIN
# ===========================================================================
def main():
    parser = argparse.ArgumentParser(description="Voice-to-G-code writing machine")
    parser.add_argument("--text", help="Skip the microphone and use this text directly")
    parser.add_argument("--preview", action="store_true",
                         help="Also save a PNG preview of the pen path")
    args = parser.parse_args()

    text = args.text.strip() if args.text else get_confirmed_text()
    if not text:
        print("No text to write. Exiting.")
        return

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    gcode_path = os.path.join(OUTPUT_DIR, f"writing_{stamp}.gcode")
    preview_path = os.path.join(OUTPUT_DIR, f"writing_{stamp}.png") if args.preview else None

    gcode = text_to_gcode(text, preview_path=preview_path)
    with open(gcode_path, "w") as f:
        f.write(gcode)

    print(f"\nG-code saved to: {gcode_path}")
    print(f"({gcode.count(chr(10)) + 1} lines of G-code)")
    print(f'Text written: "{text}"')


if __name__ == "__main__":
    main()

# ===========================================================================
# SETUP (one-time)
# ===========================================================================
# 1. Install the Python packages:
#       pip install vosk sounddevice matplotlib numpy
#
#    On Windows, sounddevice usually installs cleanly via pip.
#    On Linux, if you hit a PortAudio error:
#       sudo apt-get install libportaudio2
#    On macOS:
#       brew install portaudio
#
# 2. Download the offline speech model (about 40 MB) and unzip it so you
#    end up with a folder named exactly "model" next to this script:
#       https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
#    -> unzip -> rename "vosk-model-small-en-us-0.15" to "model"
#    (more model choices, incl. other languages/accents, are listed at
#    https://alphacephei.com/vosk/models)
#
# 3. Run it:
#       python voice_to_gcode.py
#    Press Enter, speak a sentence, press Enter again. Confirm the text
#    it recognized (or re-record, or type it manually), and it writes
#    gcode_output/writing_<timestamp>.gcode
#
# 4. Stream that file to your GRBL controller with any GRBL sender
#    (e.g. Universal G-code Sender, Candle, or CNCjs) to plot it.
