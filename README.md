During meetings, we may often forget a specific detail that someone mentioned. The purpose of this project is to ensure that you're not missing anything from your meetings, so that you're keeping up efficiently and productively.

You sit through a lot of spoken content worth keeping: tutoring classes, lectures, Zoom meetings, stand-ups. Taking notes live is time-consuming, distracting, and lossy. This project lets you:

1. Record the session (built-in capture, or bring your own .mp3/.wav/.m4a (eg from OBS)).
2. Transcribe it to text on your own GPU/CPU! A private, free, multilingual solution.
3. [optional] Summarize the transcript into structured notes (topics, takeaways, action items).

> **Note:** recording, and transcription are fully local, but the summarizaiton step relies on an LLM API key. If you don't know what that is, you can just paste the transcript text file into an LLM chatbox.

---

## Process

Record a class/meeting/tutoring session/etc, then transcribe it locally with [faster-whisper](https://github.com/SYSTRAN/faster-whisper), which is then sumarized into clean notes by an LLM like ChatGPT, Gemini, Claude, etc.

Furthermore, the audio recorded is entirely private on your machine: transcription occurs locally. It also works for any language the OpenAI's whisper supports.

> To try this project without installing any dependencies, [download the prebuilt windows exe!](https://github.com/eric-feng14/audio_transcribe/releases/latest)
>
> When testing the demo build, make sure to follow the README embedded!

If you want to explore this project even further, you can build and run this from source. Follow the procedure below.

---

## QUICK START PROCEDURE

```powershell
# 1. One-time setup (creates venv, installs dependencies, makes your .env)
powershell -ExecutionPolicy Bypass -File setup.ps1

# 2. (optional) open .env and paste your Anthropic API key for summaries. Again, this step is correlates to the summarization step; pasting the transcript text file into an LLM also works!

# 3. Run the whole pipeline — record now, then auto transcribe.
.\venv\Scripts\python.exe run.py
```

Alternatively, if that is too complex, just double click `run.bat`. It will open a terminal window and start recording until you press Enter. Next, it automatically transcribes the audio file and summarizes it (if possible), dropping the results in `recordings/`, `transcripts/`, and `summaries/`.

---

## Setup & Further Configuration

Everything below has already been handled by `setup.ps1`; this section explains what it does and what you can change, so you can do it manually or troubleshoot.

### 1. Prerequisites

- **Windows** for the built-in recording (it uses WASAPI loopback). Transcription and summarization work on any OS. If you're on a different OS like linux or mac, it is reccomended that you record audio with open source software like OBS.
- **Python 3.13** — install from [python.org](https://www.python.org/downloads/) and check "Add Python to PATH" during install. Newer versions of python should work, but python 3.13 is the best option as this is what version the project was built off of.
- *(Optional)* an **NVIDIA GPU** for fast transcription. No GPU (or an AMD GPU) is fine — it
  falls back to CPU automatically.

### 2. Environment creation + dependencies

```powershell
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

The `large-v3` Whisper model (~3 GB) downloads automatically the first time you transcribe and
is cached after that.

### 3. Summary

Summaries use Claude. Copy `.env.example` to `.env` and add your key (from
[console.anthropic.com](https://console.anthropic.com)):

```
ANTHROPIC_API_KEY=sk-ant-...
```

If you don't have a key, run with `--no-summarize` to get recording + transcript. You can then paste the transcript text file into an LLM chatbox.

### 4. Transcription model

The defaults work for most people (auto-detect GPU, best model). Override per run with flags,
or persistently in `.env`:

| Setting | `.env` variable | Flag | Options |
|---|---|---|---|
| Whisper model | `WHISPER_MODEL` | `--model` | `large-v3` (best), `medium`, `small`, `base`, `tiny` (smaller = faster, less accurate) |
| Device | `WHISPER_DEVICE` | `--device` | `auto` (default), `cuda` (force NVIDIA), `cpu` (force CPU) |
| Summary model | `CLAUDE_MODEL` | `--claude-model` | any Anthropic model id |

**Which to pick:**

- **NVIDIA GPU:** leave defaults (`auto` → CUDA, `large-v3`). Fast and most accurate.
- **No GPU / AMD GPU / Mac:** it auto-falls back to CPU. `large-v3` on CPU is accurate but
  slow (~real-time); for quicker results use a smaller model, e.g. `--model medium` or
  `--model small`. (faster-whisper's GPU backend is NVIDIA-only, so AMD GPUs use the CPU.)

Example:

```powershell
.\venv\Scripts\python.exe run.py --device cpu --model medium
```

### 5. CUDA Libraries

The GPU path needs cuBLAS / cuDNN, which ship as the `nvidia-cublas-cu12` and
`nvidia-cudnn-cu12` pip packages (already in `requirements.txt`). [transcribe.py](transcribe.py)
locates them inside your environment automatically and adds them to the DLL search path — no
manual path editing needed. If you ever see a "could not load cudnn" error, reinstall them:

```powershell
.\venv\Scripts\python.exe -m pip install nvidia-cublas-cu12 nvidia-cudnn-cu12
```

---

## Usage

> **The easy way:** `python run.py` (or double-click `run.bat`) does record → transcribe → summarize in one go. The sections below describe running each stage on its own, which is handy for processing existing files or customizing a step.

### One-command pipeline (`run.py`)

```powershell
python run.py                  # record now (Enter to stop) -> transcribe -> summarize
python run.py --seconds 3600   # record 1 hour, then transcribe + summarize
python run.py meeting.wav      # process an existing audio file (skip recording)
python run.py --zoom           # auto-record EVERY Zoom meeting, then transcribe + summarize
python run.py --no-summarize   # stop after transcribing (no API key needed)
python run.py --name lesson1   # control the output base name
```

---

## Running each tool separately

`run.py` ties everything together, but each stage is its own script you can run on its own —
useful for recording without processing, transcribing a file you already have, or
re-summarizing an existing transcript. (Examples below assume the venv is active, i.e.
`.\venv\Scripts\Activate.ps1`; otherwise prefix commands with `.\venv\Scripts\python.exe`.)

### `run.py` — full pipeline

`python run.py [input] [options]`

| Argument | Description |
|---|---|
| `input` | *(optional)* existing audio file to process; if omitted, records first |
| `--zoom` | continuously auto-record every Zoom meeting, then process each |
| `--seconds N` | record for N seconds instead of until you press Enter |
| `--name NAME` | base name for the output files (default: a timestamp) |
| `--no-summarize` | stop after transcribing (no API key needed) |
| `--no-mic` | record system audio only |
| `--no-system` | record microphone only |
| `--model NAME` | Whisper model (see transcribe.py below) |
| `--device DEV` | `auto` / `cuda` / `cpu` |
| `--claude-model NAME` | Anthropic model for the summary |

### `recorder.py` — record audio only

Captures **system audio + your microphone mixed** into one `.wav`, the way OBS mixes
"Desktop Audio" + "Mic". The `output` path is required.

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

Runs in the background and watches for Zoom's in-meeting process (`CptHost.exe`, which only
exists while you're *in* a meeting). On detection it pops a Windows notification, records
system + mic, and stops when the meeting ends. Saves to `recordings\zoom_<timestamp>.wav`.
Stop the watcher with **Ctrl+C**. (Takes no positional arguments.)

`python watch_zoom.py [--transcribe]`

| Argument | Description |
|---|---|
| `--transcribe` | also transcribe each recording when the meeting ends |

```powershell
python watch_zoom.py                # record only
python watch_zoom.py --transcribe   # record + transcribe each meeting
```

> For record + transcribe **+ summarize** of every meeting, use `python run.py --zoom`.

### `transcribe.py` — audio → text

Runs faster-whisper, **auto-detects the language** (no language flag — important when you
record different languages), and uses **VAD** to skip silence so quiet stretches don't
produce hallucinated text. Writes timestamped lines like `[0:01:23] some spoken text`.

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

Sends the transcript to Claude and writes Markdown notes with **Main topics**, **Key
takeaways**, **Action items / homework**, and **Questions & sticking points**. Long
transcripts are summarized in chunks and then combined, so multi-hour sessions don't exceed
the context window. Requires `ANTHROPIC_API_KEY` (see [Setup](#3-summary)).

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

## How recording works (OBS-grade audio)

The recorder is built to be reliable for long, multi-hour sessions:

- **Continuous loopback via a silent keep-alive.** WASAPI loopback delivers no samples while
  the output is idle. The recorder continuously renders inaudible digital silence to the
  output device, keeping the audio engine active so the system track is unbroken — real
  silence during pauses, audio during speech — instead of audio "sliding" to the start.
- **Drift correction (like OBS).** The mic and speakers run on separate hardware clocks that
  slowly drift apart (~0.2–1 s over a few hours if uncorrected). Each stream is timestamped
  and resampled to its measured wall-clock duration, then aligned on a shared timeline, so the
  two voices stay in sync for the whole recording.
- **Streamed to disk, crash-safe.** Audio is written to per-stream raw files as it arrives
  (flat memory, ~14 MB regardless of length) and drift-corrected/mixed in a low-memory
  post-pass when you stop. A crash leaves recoverable raw audio on disk. You'll briefly see
  `*.raw.wav` temp files during recording — they're deleted automatically on success.

### Recording notes / limitations

- **Windows-only** (WASAPI loopback). Other OSes need a different capture backend.
- Captures whatever plays through your **default speakers** and **default mic** — set those
  before recording.
- Zoom detection keys on the `CptHost.exe` process name. If a Zoom update renames it, edit
  `ZOOM_MEETING_PROCESS` in [watch_zoom.py](watch_zoom.py). The same pattern works for other
  apps (e.g. Teams' `ms-teams.exe`).
- Remaining known gap vs OBS: no handling of mid-recording buffer drops (xruns), which are
  rare on an idle machine.

### CPU-only (no GPU)

No configuration needed — `--device auto` (the default) falls back to CPU when no NVIDIA GPU
is present. To force it, or to speed it up with a smaller model:

```powershell
python run.py --device cpu --model medium
```

---

## Building the executable

The [downloadable release](https://github.com/eric-feng14/audio_transcribe/releases/latest) is built with
[PyInstaller](https://pyinstaller.org/) from [pyinstaller_entry.py](pyinstaller_entry.py)
(a thin wrapper that defaults the bundled app to CPU + the `small` model) using
[audio_transcribe.spec](audio_transcribe.spec). To reproduce it:

```powershell
powershell -ExecutionPolicy Bypass -File setup.ps1   # venv + deps (once)
.\venv\Scripts\python.exe -m pip install pyinstaller
.\venv\Scripts\pyinstaller.exe audio_transcribe.spec --clean --noconfirm
```

The app lands in `dist\audio_transcribe\` (a single folder with `audio_transcribe.exe`); zip
that folder to produce the release asset. The CUDA libraries are intentionally **not** bundled
(they're multiple GB), which is why the prebuilt exe runs on CPU; running from source still
uses your GPU automatically.

---

## Ideas for later

- **Speaker diarization** ("who said what") via [whisperX](https://github.com/m-bain/whisperX)
  or `pyannote.audio` — labels like "Tutor:" / "Student:", a big win for tutoring summaries.
- **Subtitle export** (`.srt`/`.vtt`) from the segment timestamps.
- **Batch mode** — transcribe/summarize every new file in `recordings/` in one run.
- **Local summarization** via Ollama for a fully offline pipeline.
- **Search index** across all transcripts ("every time we covered Mary Shelley").
- **xrun handling** in the recorder for heavy, unattended multi-hour captures.
