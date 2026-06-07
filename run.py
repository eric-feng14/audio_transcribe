"""
run.py — one-command pipeline: record → transcribe → summarize.

This is the main entry point. Typical use:

    python run.py                 # record now (press Enter to stop), then transcribe + summarize
    python run.py --seconds 3600  # record for 1 hour, then transcribe + summarize
    python run.py meeting.wav     # process an existing audio file (skip recording)
    python run.py --zoom          # auto-record every Zoom meeting, then transcribe + summarize

Useful flags:
    --no-summarize     stop after transcribing (no LLM, no API key needed)
    --no-mic           record system audio only
    --device cpu       force CPU transcription (e.g. AMD GPU / no GPU)
    --model medium     smaller/faster Whisper model
    --name lesson1     base name for the output files

Outputs go to recordings/<name>.wav, transcripts/<name>.txt, summaries/<name>.md.
"""

import argparse
import datetime as dt
import sys
import threading
from pathlib import Path

import recorder
import summarize
import transcribe

RECORDINGS_DIR = Path("recordings")
TRANSCRIPTS_DIR = Path("transcripts")
SUMMARIES_DIR = Path("summaries")


def _record(wav_path, seconds, mic, system):
    """Record to wav_path; if seconds is None, stop on Enter."""
    wav_path.parent.mkdir(parents=True, exist_ok=True)
    stop = threading.Event()
    if seconds is None:
        print("Recording... press Enter to stop.")
        threading.Thread(target=lambda: (input(), stop.set()), daemon=True).start()
    else:
        print(f"Recording for {seconds}s...")
    recorder.record(str(wav_path), stop_event=stop, seconds=seconds, mic=mic, system=system)
    print(f"Saved recording: {wav_path}")


def process(wav_path, name, do_summarize, whisper_model, device, claude_model):
    """Transcribe (and optionally summarize) a finished audio file."""
    wav_path = Path(wav_path)
    TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
    txt_path = TRANSCRIPTS_DIR / f"{name}.txt"

    print("\nTranscribing...")
    transcribe.transcribe(str(wav_path), str(txt_path), model=whisper_model, device=device)

    if not do_summarize:
        return
    SUMMARIES_DIR.mkdir(parents=True, exist_ok=True)
    md_path = SUMMARIES_DIR / f"{name}.md"
    print("\nSummarizing...")
    try:
        summarize.summarize_file(str(txt_path), str(md_path), model=claude_model)
    except RuntimeError as e:
        print(f"Skipping summary: {e}")


def main():
    ap = argparse.ArgumentParser(description="Record -> transcribe -> summarize in one command.")
    ap.add_argument("input", nargs="?", help="existing audio file to process (skip recording)")
    ap.add_argument("--zoom", action="store_true", help="auto-record every Zoom meeting")
    ap.add_argument("--seconds", type=int, help="record for a fixed number of seconds")
    ap.add_argument("--name", help="base name for output files (default: timestamp)")
    ap.add_argument("--no-summarize", action="store_true", help="transcribe only, no LLM summary")
    ap.add_argument("--no-mic", action="store_true", help="record system audio only")
    ap.add_argument("--no-system", action="store_true", help="record microphone only")
    ap.add_argument("--model", default=transcribe.DEFAULT_MODEL, help="Whisper model")
    ap.add_argument("--device", default=transcribe.DEFAULT_DEVICE, choices=["auto", "cuda", "cpu"])
    ap.add_argument("--claude-model", default=summarize.DEFAULT_MODEL, help="Anthropic model for summaries")
    args = ap.parse_args()

    do_summarize = not args.no_summarize

    # Mode 1: continuously auto-record Zoom meetings.
    if args.zoom:
        import watch_zoom

        def on_saved(wav_path):
            name = Path(wav_path).stem
            process(wav_path, name, do_summarize, args.model, args.device, args.claude_model)

        try:
            watch_zoom.watch(on_saved=on_saved)
        except KeyboardInterrupt:
            print("\nStopped watching.")
        return

    # Mode 2: process an existing file.
    if args.input:
        name = args.name or Path(args.input).stem
        process(args.input, name, do_summarize, args.model, args.device, args.claude_model)
        return

    # Mode 3: record now, then process.
    name = args.name or dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    wav_path = RECORDINGS_DIR / f"{name}.wav"
    _record(wav_path, args.seconds, mic=not args.no_mic, system=not args.no_system)
    process(wav_path, name, do_summarize, args.model, args.device, args.claude_model)


if __name__ == "__main__":
    main()
