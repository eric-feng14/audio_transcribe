## Background Information

During meetings, we may often forget a specific detail that someone mentioned. The purpose of this project is to ensure that you're not missing anything from your meetings, so that you're keeping up efficiently and productively. There is a ton of content throughout our meetings that is worth keeping! For example, tutoring classes, lectures, zoom meetings, google meetings, etc. Taking notes in real time is time-consuming, distracting, and inefficient. This project lets you:

1. Record the meeting
2. Transcribe it to text locally
3. Optionally summarize the transcript into structured notes

---

## Overview

Record a meeting session via recorder.py or locally (eg OBS), then transcribe it locally with [faster-whisper](https://github.com/SYSTRAN/faster-whisper), which is then sumarized into clean notes by an LLM like ChatGPT, Gemini, Claude, etc. Furthermore, the audio recorded is entirely private on your machine, as transcription occurs locally. It also works for any language the OpenAI's whisper model supports.

For testers who want to quickly try this project without installing any dependencies, [download the prebuilt windows exe!](https://github.com/eric-feng14/audio_transcribe/releases/latest). When testing the demo, make sure to follow the README.

If you want to explore this project even further, you can build and run this from source. Follow the procedure below.

---

## Process
1. Double click "run.bat". It will open a terminal window and start recording until you press enter to quit. Next, it transcribes the audio file and summarizes it if possible, dropping the results into the recordings/, transcripts/, and summaries/ directories respectively. 


For a more manual approach, follow the powershell commands below. Note the optional step is for the LLM summaries.
```powershell
powershell -ExecutionPolicy Bypass -File setup.ps1

#(optional) open .env and paste your Anthropic API key for summaries.

.\venv\Scripts\python.exe run.py
```

---

## Setup & Further Configuration (manual)

1. Prerequisites:
- windows os is reccomended. Other operating systems are okay, but you will have to record the audio on software like OBS.
- Python 3.13, install from python.org and make sure to add python to path during install. Newer versions of python should be fine too.
- NVIDIA GPU is optional but helps speed up the transcription process significantly. I personally have a 4070 ti.

2. Dependencies
Follow the powershell commands below:
```powershell
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

3. Summary (optional)
- Note: summaries use claude
Copy .env.example to .env and add your personal key from console.anthropic.com
Important: If you don't have a key, run with --no-summarize to get recording + transcript only. Then paste the transcript.txt into an LLM Chatbox.

4. Transcription model 
- defaults should be fine for most people. However you can customize which OpenAI whisper model you choose to run on your computer with flags. 
Below is a table detailing the different flags. If you understand computers decently well, you should be able to understand the larger models are harder to run. So choose accordingly with your hardware. Obviously faster is better if your computer can handle it.

| Setting | `.env` variable | Flag | Options |
|---|---|---|---|
| Whisper model | `WHISPER_MODEL` | `--model` | `large-v3` (best), `medium`, `small`, `base`, `tiny` (smaller = faster, less accurate) |
| Device | `WHISPER_DEVICE` | `--device` | `auto` (default), `cuda` (force NVIDIA), `cpu` (force CPU) |
| Summary model | `CLAUDE_MODEL` | `--claude-model` | any Anthropic model id |

Example:

```powershell
.\venv\Scripts\python.exe run.py --device cpu --model medium
```

5. CUDA Libraries (if you had an issue earlier with requirements.txt)
If you're a goat and have an NVIDIA GPU, read here. 

The GPU path needs cuBLAS / cuDNN, which ship as the `nvidia-cublas-cu12` and
`nvidia-cudnn-cu12` pip packages (already in `requirements.txt`). [transcribe.py](transcribe.py)
locates them inside your environment automatically and adds them to the DLL search path — no
manual path editing needed. If you ever see a "could not load cudnn" error, reinstall them:

```powershell
.\venv\Scripts\python.exe -m pip install nvidia-cublas-cu12 nvidia-cudnn-cu12
```

---

## Usage

run.py flags 

```powershell
python run.py                  # record now -> transcribe -> summarize
python run.py --seconds 3600   # record 1 hour, then transcribe + summarize
python run.py meeting.wav      # process an existing audio file (skip recording)
python run.py --zoom           # auto-record EVERY Zoom meeting, then transcribe + summarize
python run.py --no-summarize   # stop after transcribing (no API key needed)
python run.py --name lesson1   # control the output base name
```

---

## Running each tool separately

run.py ties the whole process together, but each stage is useful on its own. For example, if you already have an audio file, or if you already have an existing transcript file, the first or second steps may not be necessary (eg you're on a different os and recorded a meeting with OBS). In these types of cases, running individual python files would be the wise choice. Before you start, make sure the venv is activated.

### `recorder.py` — record audio only
This file captures both the system audio and your microphone audio into one .wave file. 

`python recorder.py <output.wav> [options]`

| Argument | Description |
|---|---|
| `output` | **(required)** path to write the `.wav` to |
| `--seconds N` | record for N seconds; omit to record until you press **Enter** |
| `--no-mic` | record system audio only (no microphone) |
| `--no-system` | record microphone only (no system audio) |

```powershell
python recorder.py recordings\lesson.wav                 # stop with Enter
python recorder.py recordings\lesson.wav --seconds 3600  # auto-stop after 1 hour
python recorder.py recordings\lesson.wav --no-mic        # system audio only
```

### `watch_zoom.py` — auto-record Zoom meetings

This python scripts run in the background and watches for Zoom's meeting process "CptHost.exe" which only exists while you're in a meeting. On detection, it pops a window notification. Once you agree to start recording, it automatically stops when the meeting ends. Stop the watcher with ctrl+c to kill the python process

`python watch_zoom.py [--transcribe]`

| Argument | Description |
|---|---|
| `--transcribe` | also transcribe each recording when the meeting ends |

```powershell
python watch_zoom.py                # record only
python watch_zoom.py --transcribe   # record + transcribe each meeting
```

### `transcribe.py` — audio → text

This file is very important as it runs faster-whisper, and auto detects the language of your meeting. It writes timestamped lines like [0:01:23] some spoken text. 

`python transcribe.py <input> [options]`

| Argument | Description |
|---|---|
| `input` | **(required)** audio file to transcribe (`.wav`/`.mp3`/`.m4a`/…) |
| `-o`, `--output PATH` | output transcript path (default: `transcript.txt`) |
| `--model NAME` | `large-v3` (default, best), `medium`, `small`, `base`, `tiny` |
| `--device DEV` | `auto` (default), `cuda` (force NVIDIA), `cpu` (force CPU) |

```powershell
python transcribe.py recordings\lesson.wav
python transcribe.py recordings\lesson.wav -o transcripts\lesson.txt
python transcribe.py recordings\lesson.wav --device cpu --model medium
```

### `summarize.py` — transcript → notes
This python file sends the transcript.txt file to claude and writes markdwon notes in a structured and organized manner. 

`python summarize.py <input> [options]`

| Argument | Description |
|---|---|
| `input` | **(required)** transcript text file |
| `-o`, `--output PATH` | output `.md` path (default: `<input>.summary.md`) |
| `--model NAME` | Anthropic model (default: `claude-sonnet-4-6`; e.g. `claude-opus-4-8` for max quality) |

```powershell
python summarize.py transcript.txt
python summarize.py transcript.txt -o summaries\lesson.md
python summarize.py transcript.txt --model claude-opus-4-8
```

### Full manual example (all three stages)

```powershell
.\venv\Scripts\Activate.ps1
python recorder.py recordings\french_0607.wav --seconds 3600
python transcribe.py recordings\french_0607.wav -o transcripts\french_0607.txt
python summarize.py transcripts\french_0607.txt -o summaries\french\french_0607.md
```

---
