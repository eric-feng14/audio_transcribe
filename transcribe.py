import argparse
import os

# Put the bundled CUDA libs (cuBLAS / cuDNN) on PATH so faster-whisper can load
# them on Windows. Must happen before importing faster_whisper.
os.environ["PATH"] = (
    r"D:\audio_transcribe\venv\Lib\site-packages\nvidia\cublas\bin" + ";" +
    r"D:\audio_transcribe\venv\Lib\site-packages\nvidia\cudnn\bin" + ";" +
    os.environ["PATH"]
)

from faster_whisper import WhisperModel


def format_timestamp(seconds):
    """Seconds -> H:MM:SS for the transcript."""
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}"


def transcribe(input_path, output_path="transcript.txt"):
    """Transcribe input_path to a timestamped text file. Returns output_path."""
    model = WhisperModel("large-v3", device="cuda", compute_type="float16")
    # vad_filter drops non-speech (silence/noise) so quiet stretches don't produce
    # hallucinated text or bogus language detection.
    segments, info = model.transcribe(input_path, vad_filter=True)
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
    args = ap.parse_args()
    transcribe(args.input, args.output)


if __name__ == "__main__":
    main()
