import argparse
import os
import sys

try:
    from dotenv import load_dotenv

    load_dotenv()  # pick up WHISPER_MODEL / WHISPER_DEVICE from a .env file if present
except ImportError:
    pass

# Defaults can be overridden by CLI flags or environment variables (see README).
DEFAULT_MODEL = os.environ.get("WHISPER_MODEL", "large-v3")
DEFAULT_DEVICE = os.environ.get("WHISPER_DEVICE", "auto")  # auto | cuda | cpu


def format_timestamp(seconds):
    """Seconds -> H:MM:SS for the transcript."""
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}"


def _resolve_device(device):
    """Resolve 'auto' to 'cuda' if an NVIDIA GPU is present, else 'cpu'."""
    if device != "auto":
        return device
    try:
        import ctranslate2  # installed with faster-whisper

        return "cuda" if ctranslate2.get_cuda_device_count() > 0 else "cpu"
    except Exception:
        return "cpu"


def _enable_cuda_libs():
    """Add the bundled cuBLAS / cuDNN folders so the CUDA DLLs load on Windows.

    The libraries ship as pip packages inside the active environment; we locate
    them relative to sys.prefix so this works wherever the project is installed
    (no hardcoded path). Harmless to call; only matters for the CUDA backend.
    """
    base = os.path.join(sys.prefix, "Lib", "site-packages", "nvidia")
    for sub in ("cublas", "cudnn"):
        path = os.path.join(base, sub, "bin")
        if os.path.isdir(path):
            os.environ["PATH"] = path + os.pathsep + os.environ["PATH"]
            if hasattr(os, "add_dll_directory"):
                os.add_dll_directory(path)


def transcribe(input_path, output_path="transcript.txt", model=DEFAULT_MODEL,
               device=DEFAULT_DEVICE, compute_type=None):
    """Transcribe input_path to a timestamped text file. Returns output_path."""
    device = _resolve_device(device)
    if compute_type is None:
        compute_type = "float16" if device == "cuda" else "int8"
    if device == "cuda":
        _enable_cuda_libs()

    from faster_whisper import WhisperModel  # imported after CUDA path is set

    print(f"Loading Whisper model '{model}' on {device} ({compute_type})...")
    whisper = WhisperModel(model, device=device, compute_type=compute_type)
    # vad_filter drops non-speech (silence/noise) so quiet stretches don't produce
    # hallucinated text or bogus language detection.
    segments, info = whisper.transcribe(input_path, vad_filter=True)
    print(f"Detected language: {info.language} (prob {info.language_probability:.2f})")

    with open(output_path, "w", encoding="utf-8") as f:
        for segment in segments:
            line = f"[{format_timestamp(segment.start)}] {segment.text.strip()}"
            f.write(line + "\n")
            print(line)
    print(f"\nSaved transcript to {output_path}")
    return output_path


def main():
    ap = argparse.ArgumentParser(description="Transcribe an audio file with faster-whisper.")
    ap.add_argument("input", help="path to the audio file to transcribe")
    ap.add_argument("-o", "--output", default="transcript.txt", help="output transcript path")
    ap.add_argument("--model", default=DEFAULT_MODEL, help=f"Whisper model (default: {DEFAULT_MODEL})")
    ap.add_argument("--device", default=DEFAULT_DEVICE, choices=["auto", "cuda", "cpu"],
                    help=f"compute device (default: {DEFAULT_DEVICE})")
    args = ap.parse_args()
    transcribe(args.input, args.output, model=args.model, device=args.device)


if __name__ == "__main__":
    main()
