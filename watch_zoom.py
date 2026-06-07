"""
watch_zoom.py — auto-record Zoom meetings.

Polls for Zoom's in-meeting process ("CptHost.exe"), which only runs while you
are actually in a meeting (the plain "Zoom.exe" runs whenever Zoom is open).
When a meeting starts it pops a Windows notification and records system audio +
mic (via recorder.py); when the meeting ends it saves the file and, with
--transcribe, transcribes it (via transcribe.py).

    python watch_zoom.py
    python watch_zoom.py --transcribe
"""

import argparse
import datetime as dt
import threading
import time
from pathlib import Path

import psutil

import transcribe      # transcription
import recorder  # audio capture

ZOOM_MEETING_PROCESS = "CptHost.exe"  # exists only while in a meeting
POLL_SECONDS = 3
RECORDINGS_DIR = Path("recordings")


def _meeting_active():
    target = ZOOM_MEETING_PROCESS.lower()
    return any((p.info["name"] or "").lower() == target for p in psutil.process_iter(["name"]))


def _notify(title, message):
    """Best-effort Windows toast; falls back to console if the lib is missing."""
    try:
        from windows_toasts import Toast, WindowsToaster

        toast = Toast()
        toast.text_fields = [title, message]
        WindowsToaster("Audio Transcribe").show_toast(toast)
    except Exception:
        print(f"[{title}] {message}")


def _record_meeting(on_saved=None):
    stamp = dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    wav_path = RECORDINGS_DIR / f"zoom_{stamp}.wav"
    _notify("Recording started", f"Zoom meeting detected -> {wav_path.name}")

    stop = threading.Event()
    rec = threading.Thread(
        target=recorder.record, args=(str(wav_path),), kwargs={"stop_event": stop}, daemon=True
    )
    rec.start()
    while _meeting_active():  # record until the meeting process disappears
        time.sleep(POLL_SECONDS)
    stop.set()
    rec.join()

    _notify("Recording saved", wav_path.name)
    print(f"Saved {wav_path}")
    if on_saved is not None:
        on_saved(wav_path)


def watch(on_saved=None):
    """Watch for Zoom meetings; record each one. on_saved(wav_path) runs after save."""
    RECORDINGS_DIR.mkdir(exist_ok=True)
    print(f"Watching for Zoom meetings (every {POLL_SECONDS}s). Ctrl+C to quit.")
    while True:
        if _meeting_active():
            _record_meeting(on_saved)
        time.sleep(POLL_SECONDS)


def _transcribe_saved(wav_path):
    try:
        transcribe.transcribe(str(wav_path), str(wav_path.with_suffix(".txt")))
    except Exception as e:
        print(f"Transcription failed ({e}). Run: python transcribe.py {wav_path}")


def main_cli():
    ap = argparse.ArgumentParser(description="Auto-record Zoom meetings.")
    ap.add_argument("--transcribe", action="store_true", help="transcribe each recording when the meeting ends")
    args = ap.parse_args()
    try:
        watch(on_saved=_transcribe_saved if args.transcribe else None)
    except KeyboardInterrupt:
        print("\nStopped watching.")


if __name__ == "__main__":
    main_cli()
