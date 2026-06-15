# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for the downloadable audio_transcribe demo executable.

Build:  .\venv\Scripts\pyinstaller.exe audio_transcribe.spec --clean --noconfirm

Produces a single-folder app under dist/audio_transcribe/ with
audio_transcribe.exe at its root. The folder is zipped and attached to the
GitHub Release. (onefile is avoided on purpose: faster-whisper / ctranslate2 /
onnxruntime ship large native DLLs that extract slowly from a onefile bundle on
every launch; a onedir build starts instantly.)
"""

from PyInstaller.utils.hooks import collect_all, collect_submodules

datas, binaries, hiddenimports = [], [], []

# Packages that carry data files and/or native DLLs we must ship whole.
for pkg in (
    "faster_whisper",   # bundles the silero VAD model under assets/
    "ctranslate2",      # native inference DLLs
    "onnxruntime",      # used by faster-whisper's VAD
    "av",               # PyAV: audio decoding (native DLLs)
    "tokenizers",
    "huggingface_hub",
    "anthropic",
    "pyaudiowpatch",    # WASAPI capture native lib
    "windows_toasts",
):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

# windows_toasts talks to WinRT via these projection packages.
for pkg in (
    "winrt.windows.ui.notifications",
    "winrt.windows.data.xml.dom",
    "winrt.windows.foundation",
    "winrt.windows.foundation.collections",
):
    hiddenimports += collect_submodules(pkg)

# The project's own modules. run.py imports these; watch_zoom is imported
# lazily inside run.main(), so name it explicitly to be safe.
hiddenimports += ["recorder", "transcribe", "summarize", "watch_zoom",
                  "numpy", "psutil", "dotenv"]

# CUDA runtime libs are huge and unused on the CPU-default frozen build.
excludes = ["nvidia", "torch", "tensorflow", "matplotlib", "tkinter",
            "PyQt5", "PySide2", "IPython", "pytest"]

a = Analysis(
    ["pyinstaller_entry.py"],
    pathex=["."],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="audio_transcribe",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="audio_transcribe",
)
