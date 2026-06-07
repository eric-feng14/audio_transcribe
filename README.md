# 🎙️ audio_transcribe

Record a class, meeting, or tutoring session → transcribe it to text **locally** with
[faster-whisper](https://github.com/SYSTRAN/faster-whisper) → summarize the transcript into
clean notes with an LLM. The audio never leaves your machine for the transcription step, and
it works for **any language** Whisper supports.

```
record (recorder.py / watch_zoom.py)  ──►  transcribe (transcribe.py)  ──►  summarize (summarize.py)
        system audio + mic, like OBS         faster-whisper, GPU         Claude → Markdown notes
```

---

## Why this exists

You sit through a lot of spoken content worth keeping: tutoring classes, lectures, Zoom
meetings, stand-ups. Taking notes live is distracting and lossy. This project lets you:

1. **Record** the session (built-in capture, or bring your own `.mp3`/`.wav`/`.m4a`).
2. **Transcribe** it to text on your own GPU/CPU — private, free, multilingual.
3. **Summarize** the transcript into structured notes (topics, takeaways, action items).

Recording and transcription are **fully local**. Only the optional summarize step sends text
(the transcript) to a cloud LLM.

---

## Requirements

- **Windows** for the built-in recording (it uses WASAPI loopback). Transcription and
  summarization work on any OS.
- **Python 3.13** (a `venv/` is included).
- An **NVIDIA GPU with CUDA** for fast transcription (`device="cuda"`). CPU works too — see
  [CPU-only](#cpu-only-no-gpu).
- The `large-v3` Whisper model (~3 GB) downloads automatically on first run and is cached.

---

## Setup

```powershell
# from the project root
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

For the **summarize** step, set your Anthropic API key (get one at
https://console.anthropic.com). Either copy `.env.example` to `.env` and fill it in:

```
ANTHROPIC_API_KEY=sk-ant-...
```

…or set it in your shell:

```powershell
$env:ANTHROPIC_API_KEY="sk-ant-..."     # this session
setx ANTHROPIC_API_KEY "sk-ant-..."     # persist for new terminals
```

The GPU build of faster-whisper needs cuBLAS / cuDNN. [transcribe.py](transcribe.py) prepends the
bundled `nvidia\cublas\bin` and `nvidia\cudnn\bin` folders to `PATH` so the DLLs load on
Windows. If you hit a "could not load cudnn" error, make sure those pip packages are
installed (they're in `requirements.txt`):

```powershell
pip install nvidia-cublas-cu12 nvidia-cudnn-cu12
```

> Note: that `PATH` patch in [transcribe.py](transcribe.py) uses an absolute `D:\audio_transcribe\...`
> path. If you clone the project elsewhere, update those two lines.

---

## Usage

### Step 1 — Record the audio

Pick whichever fits. Both capture **system audio + your microphone mixed** into one `.wav`,
the way OBS mixes "Desktop Audio" + "Mic".

**A. Auto-record Zoom meetings** ([watch_zoom.py](watch_zoom.py)) — hands-off. Leave it
running; it watches for Zoom's in-meeting process (`CptHost.exe`, which only exists while
you're *in* a meeting), pops a Windows notification, records, and stops when the meeting ends.

```powershell
python watch_zoom.py                # saves recordings\zoom_<timestamp>.wav
python watch_zoom.py --transcribe   # also transcribe automatically when the meeting ends
```

**B. Manual recording** ([recorder.py](recorder.py)) — for in-person classes or any session:

```powershell
python recorder.py recordings\lesson.wav              # stop with Enter
python recorder.py recordings\lesson.wav --seconds 3600   # auto-stop after 1 hour
python recorder.py recordings\lesson.wav --no-mic     # system audio only
python recorder.py recordings\lesson.wav --no-system  # mic only
```

**C. Bring your own file** — already have audio from your phone, OBS, etc.? Skip to Step 2.

### Step 2 — Transcribe to text

```powershell
python transcribe.py recordings\lesson.wav
python transcribe.py recordings\lesson.wav -o transcripts\lesson.txt   # choose output
```

- Runs on your GPU, **auto-detects the language** (no language flag — important when you
  record different languages), and uses **VAD** (`vad_filter=True`) to skip silence so quiet
  stretches don't produce hallucinated text.
- Writes timestamped lines like `[0:01:23] some spoken text` (default: `transcript.txt`).

### Step 3 — Summarize into notes

```powershell
python summarize.py transcript.txt
python summarize.py transcript.txt -o summaries\lesson.md
python summarize.py transcript.txt --model claude-opus-4-8   # max quality
```

Sends the transcript to Claude and writes Markdown notes with **Main topics**, **Key
takeaways**, **Action items / homework**, and **Questions & sticking points**. Long
transcripts are summarized in chunks and then combined, so multi-hour sessions don't exceed
the context window. Default model is `claude-sonnet-4-6` (good quality/cost balance).

### Full example

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

Edit [transcribe.py](transcribe.py):

```python
model = WhisperModel("large-v3", device="cpu", compute_type="int8")
```

`int8` keeps it reasonably fast on CPU; a smaller model (`medium`, `small`) trades accuracy
for speed.

---

## Project layout

```
audio_transcribe/
├── recorder.py          # capture system audio + mic to a WAV (OBS-style)
├── watch_zoom.py        # auto-record Zoom meetings on detection
├── transcribe.py              # transcribe audio → timestamped text (faster-whisper, GPU)
├── summarize.py         # transcript → Markdown notes (Claude)
├── requirements.txt     # Python dependencies
├── .env.example         # template for ANTHROPIC_API_KEY
├── recordings/          # captured audio (gitignored)
├── summaries/           # generated notes, by subject (english/, french/)
└── venv/                # Python 3.13 virtual environment
```

---

## Privacy & consent

Recording and transcription run entirely on your machine. The **summarize** step sends the
transcript text to Anthropic — avoid it for sensitive recordings, or swap in a local model
(e.g. [Ollama](https://ollama.com)). Always make sure you have consent to record other people.

---

## Ideas for later

- **Speaker diarization** ("who said what") via [whisperX](https://github.com/m-bain/whisperX)
  or `pyannote.audio` — labels like "Tutor:" / "Student:", a big win for tutoring summaries.
- **Subtitle export** (`.srt`/`.vtt`) from the segment timestamps.
- **Batch mode** — transcribe/summarize every new file in `recordings/` in one run.
- **Local summarization** via Ollama for a fully offline pipeline.
- **Search index** across all transcripts ("every time we covered Mary Shelley").
- **xrun handling** in the recorder for heavy, unattended multi-hour captures.
