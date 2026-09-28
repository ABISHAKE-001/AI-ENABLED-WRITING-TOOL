# AI-Enabled Writing Tool

An **AI-enabled voice-controlled writing machine** that converts spoken language into machine-readable **G-code** and generates automated handwriting using a pen-plotter mechanism.

The system combines **offline speech recognition, text processing, vector path generation, G-code generation, and CNC/plotter control** to create a complete voice-to-physical-writing pipeline.

---

## 🚀 Project Overview

The AI-Enabled Writing Tool is designed to allow a user to **speak a sentence**, convert the speech into text, preview the recognized content, and automatically generate a G-code file that can be executed by a CNC/pen-plotter machine.

### Basic workflow

```text
        🎤 Microphone
              │
              ▼
     Offline Speech Recognition
            (Vosk)
              │
              ▼
        Recognized Text
              │
              ▼
       User Confirmation
              │
              ▼
      Text → Vector Paths
        (Matplotlib)
              │
              ▼
        G-code Generation
              │
              ▼
       G-code File (.gcode)
              │
              ▼
       GRBL / CNC Controller
              │
              ▼
       ✍️ Automated Writing
```

The system works **offline** for speech recognition, making it suitable for applications where internet connectivity is unavailable or unreliable.

---

## ✨ Key Features

* 🎤 **Voice-controlled writing**
* 🤖 **Offline speech recognition using Vosk**
* 📝 Converts spoken sentences into editable text
* 🔄 Option to **re-record** incorrect speech
* ⌨️ Supports manual text input
* 📐 Converts text into vector-based writing paths
* ⚙️ Automatically generates G-code
* ✍️ Supports pen-up and pen-down control
* 📄 Supports A4-sized writing area
* 📏 Automatic text wrapping based on page width
* 👀 Generates an optional PNG path preview
* 🗂️ Automatically creates timestamped G-code files
* 📴 No cloud-based speech recognition required
* 🛠️ Compatible with GRBL-based CNC/plotter systems

---

## 🧠 AI / Intelligent Processing

The project uses **Vosk**, an offline speech-recognition engine, to convert human speech into text.

For example:

```text
User Speech:
"Hello from the writing machine"

             ↓

Vosk Speech Recognition

             ↓

Recognized Text:
"hello from the writing machine"

             ↓

Vector Path Generation

             ↓

G-code

             ↓

Pen Plotter

             ↓

Physical Handwriting
```

The speech-recognition stage allows the machine to understand natural voice input without requiring an internet connection.

---

## 🏗️ System Architecture

The software is divided into multiple processing stages.

### 1. Voice Capture

The system uses a microphone to capture the user's speech.

Python's `sounddevice` library provides real-time audio input.

```python
sounddevice
       │
       ▼
16 kHz Mono Audio
       │
       ▼
Vosk Recognizer
```

The audio is sampled at:

```text
Sample Rate = 16000 Hz
Channels    = 1
Format      = 16-bit Integer
```

---

### 2. Offline Speech Recognition

The captured audio is processed using the **Vosk speech-recognition engine**.

The project loads a locally stored Vosk model:

```text
model/
```

The recognizer processes the audio and generates the corresponding text.

Example:

```text
Audio:
"Write hello from the machine"

↓

Recognized text:
"write hello from the machine"
```

Because the model is stored locally, the speech-recognition process does not require an internet connection.

---

### 3. Text Confirmation

After speech recognition, the system displays the recognized sentence.

The user can select:

```text
[y] Yes
[r] Re-record
[t] Type manually
```

This provides an additional validation stage before generating the writing path.

Example:

```text
Recognized:
"hello from the writing machine"

Use this?
[y]es / [r]e-record / [t]ype instead:
```

This helps prevent incorrect speech recognition from being directly converted into machine movement.

---

## 📐 Text-to-Vector Conversion

Once the text is confirmed, the system converts the characters into vector outlines.

The project uses:

```python
matplotlib.textpath.TextPath
```

The text is represented as geometric paths rather than ordinary bitmap images.

For example:

```text
Text

HELLO

↓

Vector outlines

H → line segments
E → line segments
L → line segments
L → line segments
O → closed outline
```

This approach allows the pen plotter to follow the geometry of each character.

---

## ✍️ Pen Path Generation

Each character is converted into one or more polygonal paths.

The machine performs two types of movement:

### Pen Up

The pen is lifted while moving between different strokes.

```gcode
G1 Z5.0
```

### Pen Down

The pen touches the paper before drawing.

```gcode
G1 Z0.0
```

The generated path therefore follows:

```text
Pen Up
   ↓
Move to starting point
   ↓
Pen Down
   ↓
Draw stroke
   ↓
Pen Up
   ↓
Move to next stroke
   ↓
Pen Down
   ↓
Draw next stroke
```

This allows the system to handle characters containing multiple separate paths and internal regions.

---

## ⚙️ G-code Generation

The generated vector paths are converted into G-code commands.

Example:

```gcode
G21
G90

G1 Z5.0 F3000
G0 X10.000 Y267.000

G1 Z0.0 F3000
G1 X10.000 Y277.000 F800
G1 X15.000 Y277.000 F800

G1 Z5.0 F3000

G0 X20.000 Y267.000
G1 Z0.0 F3000
...
```

### Important G-code commands

| Command | Purpose                    |
| ------- | -------------------------- |
| `G21`   | Set units to millimeters   |
| `G90`   | Absolute positioning       |
| `G0`    | Rapid movement             |
| `G1`    | Controlled linear movement |
| `Z5.0`  | Pen up                     |
| `Z0.0`  | Pen down                   |
| `F800`  | Drawing feed rate          |
| `F3000` | Travel feed rate           |
| `M2`    | Program end                |

---

## 📄 A4 Page Layout

The software is configured for an A4-sized writing area.

```text
Page Width  = 210 mm
Page Height = 297 mm

Writing Area:
Width  = 190 mm
Height = 277 mm

Margin = 10 mm
```

The system automatically wraps text when it reaches the configured page width.

### Text parameters

```python
FONT_SIZE_MM = 10
LINE_HEIGHT_MM = 14

PAGE_WIDTH_MM = 190
PAGE_HEIGHT_MM = 277

MARGIN_X = 10
MARGIN_Y = 10
```

This allows longer sentences to automatically continue on subsequent lines.

---

## 👀 G-code Path Preview

The project optionally generates a PNG preview of the expected pen movement.

Run:

```bash
python voice_to_gcode.py --text "Hello from the writing machine" --preview
```

The system generates:

```text
writing_YYYYMMDD_HHMMSS.gcode
writing_YYYYMMDD_HHMMSS.png
```

The PNG provides a visual representation of the generated pen path before the G-code is sent to the machine.

---

## 🧪 Test Mode

The microphone is not required for testing.

Text can be supplied directly through the command line:

```bash
python voice_to_gcode.py --text "Hello from the writing machine"
```

This is useful for testing the G-code generation and plotter mechanism independently of the speech-recognition system.

---

## 🎤 Voice Mode

To run the complete voice-controlled system:

```bash
python voice_to_gcode.py
```

The program will:

1. Initialize the Vosk speech model.
2. Wait for the user to press Enter.
3. Start microphone recording.
4. Capture the spoken sentence.
5. Convert speech to text.
6. Display the recognized sentence.
7. Ask the user for confirmation.
8. Convert the text into vector paths.
9. Generate G-code.
10. Save the G-code inside the output directory.

---

## 📁 Project Structure

Recommended project structure:

```text
AI-Writing-Tool/
│
├── voice_to_gcode.py
│
├── model/
│   ├── am/
│   ├── conf/
│   ├── graph/
│   ├── ivector/
│   └── ...
│
├── gcode_output/
│   ├── writing_20260928_182000.gcode
│   └── writing_20260928_182000.png
│
└── README.md
```

---

## 🛠️ Technologies Used

### Programming

* Python
* Object-oriented and procedural Python programming
* File handling
* Command-line argument processing
* Multithreading
* JSON processing

### Artificial Intelligence

* Vosk Offline Speech Recognition
* Speech-to-Text processing

### Graphics / Vector Processing

* Matplotlib
* `TextPath`
* `FontProperties`

### Audio

* SoundDevice
* Microphone input
* 16 kHz mono audio processing

### CNC / Automation

* G-code
* GRBL
* CNC/pen plotter control
* Cartesian motion control

---

## 📦 Software Requirements

Install the required Python packages:

```bash
pip install vosk sounddevice matplotlib numpy
```

### Requirements

```text
Python 3.x
Microphone
Vosk speech model
Windows / Linux / macOS
GRBL-based plotter (for physical writing)
```

---

## 🧩 Vosk Model Setup

Download a Vosk English speech model and extract it into the project directory.

The final structure should be:

```text
AI-Writing-Tool/
│
├── voice_to_gcode.py
│
└── model/
```

The program expects the model directory at:

```python
MODEL_PATH = os.path.join(BASE_DIR, "model")
```

This makes the program independent of the terminal's current working directory.

---

## ⚡ Configuration

The main machine parameters can be modified inside the Python file.

### Writing size

```python
FONT_SIZE_MM = 10
```

### Line spacing

```python
LINE_HEIGHT_MM = 14
```

### Drawing speed

```python
FEED_DRAW = 800
```

### Pen movement speed

```python
FEED_MOVE = 3000
```

### Pen positions

```python
PEN_UP_Z = 5.0
PEN_DOWN_Z = 0.0
```

These values can be adjusted depending on the mechanical design of the writing machine.

---

## 🔧 Servo-Based Pen Control

The current implementation assumes a Z-axis mechanism for pen movement.

For a servo-controlled pen mechanism, the generated commands can be modified to use GRBL spindle/servo commands.

For example:

```text
Pen Up:
M5

Pen Down:
M3 S1000
```

The exact commands depend on the GRBL controller and servo configuration.

---

## 🔄 Complete Working Pipeline

```text
┌─────────────────────┐
│      User Speech    │
│    🎤 Microphone    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   SoundDevice       │
│  Audio Acquisition  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│       Vosk          │
│ Offline Speech AI   │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Recognized Text     │
│ Confirmation        │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Matplotlib TextPath │
│ Vector Generation   │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   G-code Generator  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ .gcode File         │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ GRBL CNC Controller │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   Pen Plotter       │
│       ✍️            │
└─────────────────────┘
```

---

## 🎯 Applications

The system can be adapted for:

* Automated handwriting
* Voice-controlled educational tools
* Assistive writing systems
* Pen plotters
* CNC-based drawing machines
* Robotic writing systems
* Accessibility-oriented interfaces
* Automated document generation
* Robotics and embedded automation demonstrations

---

## 🔮 Future Improvements

Possible improvements include:

* Support for multiple languages
* Improved handwriting-style fonts
* Real-time speech recognition
* Direct G-code streaming to GRBL
* Automatic page detection
* Automatic pen pressure control
* Servo-based pen lifting
* Raspberry Pi-based standalone operation
* LCD/touchscreen interface
* Wi-Fi-based G-code transfer
* Handwriting personalization
* AI-based handwriting style generation
* Automatic error correction for speech recognition
* Camera-based paper alignment
* Closed-loop position correction

---

## 📊 Project Highlights

| Feature            | Implementation         |
| ------------------ | ---------------------- |
| Speech Input       | Microphone             |
| Speech Recognition | Vosk                   |
| AI Processing      | Offline Speech-to-Text |
| Text Processing    | Python                 |
| Vector Generation  | Matplotlib TextPath    |
| Machine Language   | G-code                 |
| Output             | Pen Plotter            |
| Page Format        | A4                     |
| Preview            | PNG                    |
| CNC Controller     | GRBL-compatible        |
| Internet Required  | No                     |

---

## 👨‍💻 Author

**Abishake C**

B.E. Mechatronics Engineering
Sri Krishna College of Engineering and Technology

### Areas of Interest

* Embedded Systems
* Robotics
* Automation
* AI/ML
* Computer Vision
* CNC and Motion Control
* Embedded Software

---

## ⭐ Project Summary

This project demonstrates the integration of **Artificial Intelligence, speech recognition, Python programming, vector processing, and robotic motion control** into a single automated writing system.

The key concept is:

> **Voice → AI Speech Recognition → Text → Vector Path → G-code → Robotic Pen Movement → Physical Writing**

The project provides a foundation for developing intelligent and accessible **voice-controlled robotic writing systems**.
