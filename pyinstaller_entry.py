"""
pyinstaller_entry.py — entry point for the bundled (frozen) executable.

This is used ONLY by the PyInstaller build that ships on the GitHub Releases
page; running the project from source still goes through run.py as documented
in the README. It exists so the downloadable .exe demos well on any Windows
machine without a manual setup:

  * Defaults the Whisper device to CPU. The CUDA backend needs the multi-GB
    cuBLAS/cuDNN libraries, which are intentionally NOT bundled (it would make
    the download enormous), so the frozen build runs on CPU. Run from source
    for GPU acceleration.
  * Defaults to the "small" Whisper model so the first-run model download and
    CPU transcription are quick. Override either with the normal flags/env, e.g.
        audio_transcribe.exe --device cpu --model large-v3
        audio_transcribe.exe meeting.wav --model medium

Both are `setdefault`s, so real environment variables and CLI flags still win.
"""

import os

os.environ.setdefault("WHISPER_DEVICE", "cpu")
os.environ.setdefault("WHISPER_MODEL", "small")

import run

if __name__ == "__main__":
    run.main()
