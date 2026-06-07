"""
summarize.py — turn a transcript into clean study/meeting notes using Claude.

Reads a transcript (e.g. the output of transcribe.py), sends it to the Anthropic API,
and writes a Markdown summary.

Setup:
    pip install anthropic
    set ANTHROPIC_API_KEY=...        # Windows (PowerShell: $env:ANTHROPIC_API_KEY="...")

Usage:
    python summarize.py transcript.txt
    python summarize.py transcript.txt -o summaries/lesson.md
    python summarize.py transcript.txt --model claude-opus-4-8

Privacy note: the transcript text is sent to Anthropic. For fully local
summarization, use a local model (e.g. via Ollama) instead.
"""

import argparse
import os
import sys

import anthropic

try:
    from dotenv import load_dotenv

    load_dotenv()  # load ANTHROPIC_API_KEY from a .env file if present
except ImportError:
    pass  # python-dotenv is optional; the env var can also be set in the shell

# Configurable default; override with --model. See Anthropic's docs for current IDs.
DEFAULT_MODEL = "claude-sonnet-4-6"

# Long transcripts are summarized in pieces, then those summaries are combined.
# ~80k characters per chunk keeps each request well within the context window.
CHUNK_CHARS = 80_000

SYSTEM_PROMPT = (
    "You are a careful note-taker. You turn raw, messy speech-to-text transcripts "
    "of classes and meetings into clear, well-structured notes. The transcript may "
    "contain transcription errors, filler words, and false starts — infer intent "
    "and ignore noise. Do not invent content that isn't supported by the transcript."
)

SUMMARY_INSTRUCTIONS = """Summarize the transcript below into Markdown notes with these sections:

## Main topics
- The key subjects covered, in order.

## Key takeaways
- The most important points, explanations, or conclusions.

## Action items / homework
- Anything assigned, agreed, or to be done next. Include who, if stated. Write "None stated" if there are none.

## Questions & sticking points
- Anything someone was confused by or that was left unresolved.

Keep it concise and skimmable. Use the speakers' own terminology.

Transcript:
"""

COMBINE_INSTRUCTIONS = """The notes below are section-by-section summaries of one long session, in order.
Merge them into a single coherent set of notes using the same Markdown structure
(## Main topics, ## Key takeaways, ## Action items / homework, ## Questions & sticking points).
Remove duplication and keep it concise.

Section summaries:
"""


def _ask_claude(client, model, instructions, body):
    message = client.messages.create(
        model=model,
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": instructions + body}],
    )
    return message.content[0].text


def _chunk(text, size):
    """Split text into <=size chunks, preferring to break on line boundaries."""
    chunks, start = [], 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            nl = text.rfind("\n", start, end)
            if nl > start:
                end = nl
        chunks.append(text[start:end])
        start = end
    return chunks


def summarize(text, client, model=DEFAULT_MODEL):
    chunks = _chunk(text, CHUNK_CHARS)
    if len(chunks) == 1:
        return _ask_claude(client, model, SUMMARY_INSTRUCTIONS, chunks[0])

    # Map: summarize each chunk. Reduce: combine the partial summaries.
    partials = []
    for i, chunk in enumerate(chunks, 1):
        print(f"Summarizing part {i}/{len(chunks)}...")
        partials.append(_ask_claude(client, model, SUMMARY_INSTRUCTIONS, chunk))
    print("Combining...")
    return _ask_claude(client, model, COMBINE_INSTRUCTIONS, "\n\n---\n\n".join(partials))


def main():
    ap = argparse.ArgumentParser(description="Summarize a transcript with Claude.")
    ap.add_argument("input", help="path to the transcript text file")
    ap.add_argument("-o", "--output", help="output .md path (default: <input>.summary.md)")
    ap.add_argument("--model", default=DEFAULT_MODEL, help=f"Anthropic model (default: {DEFAULT_MODEL})")
    args = ap.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("Error: set the ANTHROPIC_API_KEY environment variable first.")

    with open(args.input, "r", encoding="utf-8") as f:
        text = f.read().strip()
    if not text:
        sys.exit(f"Error: {args.input} is empty.")

    output = args.output or os.path.splitext(args.input)[0] + ".summary.md"
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from the environment

    summary = summarize(text, client, model=args.model)

    parent = os.path.dirname(output)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(output, "w", encoding="utf-8") as f:
        f.write(summary + "\n")
    print(f"\nSaved summary to {output}")


if __name__ == "__main__":
    main()
