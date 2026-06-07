"""
recorder.py — capture system audio (loopback) + microphone, mixed into one WAV.

Windows-only. Uses WASAPI loopback via PyAudioWPatch so it can record everything
you hear (Zoom participants, videos, the tutor) together with your microphone,
the same way OBS mixes "Desktop Audio" + "Mic".

How it stays reliable for long, multi-hour recordings (OBS-style):

  * A silent keep-alive renderer keeps the WASAPI engine active, so the loopback
    stream is continuous (real silence during pauses) instead of full of gaps.
  * Each captured stream is written straight to its own raw WAV on disk as it
    arrives, via a background writer thread. Memory stays flat regardless of
    length, and if the process is killed mid-recording the raw audio is already
    on disk (the .sys/.mic ".raw.wav" files) and can be recovered.
  * When recording stops, a low-memory chunked post-pass applies drift correction
    (resampling each stream to its measured wall-clock duration) and mixes the
    streams onto one common timeline, then deletes the raw files.

Standalone usage:

    python recorder.py output.wav          # record until you press Enter
    python recorder.py output.wav --seconds 60
    python recorder.py output.wav --no-mic # system audio only
"""

import argparse
import os
import queue
import threading
import time
import wave

import numpy as np
import pyaudiowpatch as pyaudio

CHUNK = 1024
TARGET_RATE = 48000      # final output sample rate
BLOCK_SECONDS = 5        # post-pass works in blocks of this many seconds (low memory)


def _find_loopback_device(p):
    """Return the WASAPI loopback device matching the default speakers."""
    wasapi = p.get_host_api_info_by_type(pyaudio.paWASAPI)
    speakers = p.get_device_info_by_index(wasapi["defaultOutputDevice"])
    if not speakers.get("isLoopbackDevice", False):
        for lb in p.get_loopback_device_info_generator():
            if speakers["name"] in lb["name"]:
                return lb
        raise RuntimeError(
            "No loopback device found. Update PyAudioWPatch / check WASAPI."
        )
    return speakers


def _find_mic_device(p):
    wasapi = p.get_host_api_info_by_type(pyaudio.paWASAPI)
    return p.get_device_info_by_index(wasapi["defaultInputDevice"])


def _open_keepalive(p):
    """Render inaudible digital silence to the default output device.

    WASAPI loopback only produces samples while something is rendering to the
    output. Continuously writing zeros keeps the audio engine active for the
    whole recording, so loopback returns an unbroken stream — the foundation of
    OBS-style continuous, drift-correctable audio. The output is pure zeros, so
    nothing is audible.
    """
    wasapi = p.get_host_api_info_by_type(pyaudio.paWASAPI)
    out = p.get_device_info_by_index(wasapi["defaultOutputDevice"])
    channels = max(1, int(out["maxOutputChannels"]))
    rate = int(out["defaultSampleRate"])

    def _callback(in_data, frame_count, time_info, status):
        return (b"\x00" * (frame_count * channels * 2), pyaudio.paContinue)  # int16 zeros

    return p.open(
        format=pyaudio.paInt16,
        channels=channels,
        rate=rate,
        output=True,
        output_device_index=out["index"],
        frames_per_buffer=CHUNK,
        stream_callback=_callback,
    )


def _open_capture(p, device, raw_path):
    """Open an input stream that streams mono int16 frames to raw_path on disk.

    The audio callback only downmixes and hands bytes to a queue; a background
    writer thread does the file I/O, so the callback never blocks on disk (which
    would risk dropped buffers). The first callback records t_start — the
    wall-clock time the first sample was captured — used later for drift
    correction and alignment.
    """
    channels = max(1, int(device["maxInputChannels"]))
    rate = int(device["defaultSampleRate"])

    wav = wave.open(raw_path, "wb")
    wav.setnchannels(1)
    wav.setsampwidth(2)
    wav.setframerate(rate)

    q = queue.Queue()
    sink = {"rate": rate, "raw_path": raw_path, "t_start": None, "wav": wav, "queue": q}

    def _writer():
        while True:
            item = q.get()
            if item is None:
                break
            wav.writeframes(item)

    writer = threading.Thread(target=_writer, daemon=True)
    writer.start()
    sink["writer"] = writer

    def _callback(in_data, frame_count, time_info, status):
        if sink["t_start"] is None:
            sink["t_start"] = time.perf_counter() - (frame_count / rate)
        arr = np.frombuffer(in_data, dtype=np.int16)
        if channels > 1:
            arr = arr.reshape(-1, channels).astype(np.int32).mean(axis=1).astype(np.int16)
        q.put(arr.tobytes())
        return (None, pyaudio.paContinue)

    sink["stream"] = p.open(
        format=pyaudio.paInt16,
        channels=channels,
        rate=rate,
        frames_per_buffer=CHUNK,
        input=True,
        input_device_index=device["index"],
        stream_callback=_callback,
    )
    return sink


def _close_capture(sink):
    sink["stream"].stop_stream()
    sink["stream"].close()
    sink["queue"].put(None)       # tell the writer thread to finish
    sink["writer"].join()
    sink["wav"].close()           # patches the WAV header (nframes) for clean files


def _add_source_block(handle, src, n0, n1, acc):
    """Add source `src`'s contribution for output samples [n0, n1) into acc.

    Reads only the slice of the raw file needed for this block, so memory stays
    bounded. The source is resampled (linear) from its native sample count to its
    drift-corrected content length, and offset by its front padding so all
    streams share one timeline.
    """
    pad = src["pad"]
    content_len = src["content_len"]
    src_len = src["src_len"]
    if content_len <= 0 or src_len <= 0:
        return
    cs = max(n0, pad)                      # first output sample in this block with content
    if cs >= n1:
        return
    o0, o1 = cs - pad, n1 - pad            # output-content index range
    src_pos = np.arange(o0, o1, dtype=np.float64) / content_len * src_len
    i0 = int(np.floor(src_pos[0]))
    i1 = min(src_len, int(np.ceil(src_pos[-1])) + 2)
    handle.setpos(i0)
    seg = np.frombuffer(handle.readframes(i1 - i0), dtype=np.int16).astype(np.float32) / 32768.0
    if seg.size == 0:
        return
    xs = np.arange(i0, i0 + seg.size)
    acc[cs - n0:n1 - n0] += np.interp(src_pos, xs, seg).astype(np.float32)


def _mixed_blocks(sources, total_len, block):
    """Yield successive mixed float32 blocks of the final timeline (streaming)."""
    handles = [wave.open(s["raw_path"], "rb") for s in sources]
    try:
        pos = 0
        while pos < total_len:
            n1 = min(pos + block, total_len)
            acc = np.zeros(n1 - pos, dtype=np.float32)
            for src, handle in zip(sources, handles):
                _add_source_block(handle, src, pos, n1, acc)
            yield acc
            pos = n1
    finally:
        for handle in handles:
            handle.close()


def _mix_with_drift(active, t_stop, output_path):
    """Drift-correct and mix the raw per-stream files into the final WAV.

    OBS-style: each stream is resampled so its sample count matches its measured
    wall-clock duration (t_stop - t_start), undoing per-device clock drift, and
    placed on a shared timeline by its own start offset. Done as a two-pass
    streaming operation (pass 1 finds the peak, pass 2 writes), so peak memory is
    one block, not the whole recording.
    """
    origin = min(s["t_start"] for s in active)
    total_len = int(round((t_stop - origin) * TARGET_RATE))

    sources = []
    for s in active:
        pad = int(round((s["t_start"] - origin) * TARGET_RATE))
        with wave.open(s["raw_path"], "rb") as wf:
            src_len = wf.getnframes()
        sources.append({
            "raw_path": s["raw_path"],
            "pad": pad,
            "src_len": src_len,
            "content_len": total_len - pad,
        })

    block = BLOCK_SECONDS * TARGET_RATE

    # Pass 1: find the peak so we only attenuate if the sum would clip.
    peak = 0.0
    for blk in _mixed_blocks(sources, total_len, block):
        if blk.size:
            peak = max(peak, float(np.abs(blk).max()))
    scale = (1.0 / peak) if peak > 1.0 else 1.0

    parent = os.path.dirname(output_path)
    if parent:
        os.makedirs(parent, exist_ok=True)

    # Pass 2: write the final WAV block by block.
    with wave.open(output_path, "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(TARGET_RATE)
        for blk in _mixed_blocks(sources, total_len, block):
            pcm = (np.clip(blk * scale, -1.0, 1.0) * 32767).astype(np.int16)
            out.writeframes(pcm.tobytes())


def record(output_path, stop_event=None, seconds=None, mic=True, system=True):
    """Record loopback + mic to output_path until stop_event is set (or seconds)."""
    p = pyaudio.PyAudio()
    sinks = []
    keepalive = None
    t_stop = None

    if stop_event is None:
        stop_event = threading.Event()

    try:
        # Keep-alive first so the engine is active before loopback capture starts.
        keepalive = _open_keepalive(p) if system else None
        if system:
            sinks.append(_open_capture(p, _find_loopback_device(p), output_path + ".sys.raw.wav"))
        if mic:
            sinks.append(_open_capture(p, _find_mic_device(p), output_path + ".mic.raw.wav"))

        if seconds is not None:
            stop_event.wait(timeout=seconds)
            stop_event.set()
        else:
            while not stop_event.is_set():
                stop_event.wait(timeout=0.1)
        t_stop = time.perf_counter()
    finally:
        if t_stop is None:
            t_stop = time.perf_counter()
        for sink in sinks:
            try:
                _close_capture(sink)
            except Exception:
                pass
        if keepalive is not None:
            keepalive.stop_stream()
            keepalive.close()
        p.terminate()

    active = [s for s in sinks if s["t_start"] is not None]
    if not active:
        raise RuntimeError("No audio captured.")

    _mix_with_drift(active, t_stop, output_path)

    # Mix succeeded — safe to remove the raw per-stream files.
    for sink in sinks:
        try:
            os.remove(sink["raw_path"])
        except OSError:
            pass
    return output_path


def main():
    ap = argparse.ArgumentParser(description="Record system audio + mic to a WAV file.")
    ap.add_argument("output", help="output .wav path")
    ap.add_argument("--seconds", type=int, default=None, help="fixed duration; omit to stop on Enter")
    ap.add_argument("--no-mic", action="store_true", help="skip microphone")
    ap.add_argument("--no-system", action="store_true", help="skip system/loopback audio")
    args = ap.parse_args()

    stop = threading.Event()
    if args.seconds is None:
        print("Recording... press Enter to stop.")
        threading.Thread(target=lambda: (input(), stop.set()), daemon=True).start()
    record(
        args.output,
        stop_event=stop,
        seconds=args.seconds,
        mic=not args.no_mic,
        system=not args.no_system,
    )
    print(f"Saved {args.output}")


if __name__ == "__main__":
    main()
