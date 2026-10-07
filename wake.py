"""
Jarvis wake word launcher.

Sits quietly and listens for "hey jarvis" using a small model that runs
on your own PC (nothing is sent to the internet while waiting).
When it hears the wake word, it starts the LiveKit agent. As soon as the
conversation ends (or the time limit is reached), it shuts the agent down
and goes straight back to waiting.
"""

import subprocess
import time
import winsound
from pathlib import Path

import numpy as np
import openwakeword
import sounddevice as sd
from openwakeword.model import Model


THRESHOLD = 0.5
MAX_SESSION_SECONDS = 180
COOLDOWN_SECONDS = 0.3


PROJECT_DIR = Path(__file__).resolve().parent
CLOSE_MARKER = PROJECT_DIR / ".session_closed"

SAMPLE_RATE = 16000
FRAME = 1280  
print("Loading wake word model (the first run downloads it)...")

try:
    openwakeword.utils.download_models()
except Exception as e:
    print(f"Model download note: {e}")

model = Model(
    wakeword_models=["hey_jarvis"],
    inference_framework="onnx",
)


def wait_for_wake_word():
    """Listen to the mic until 'hey jarvis' is heard."""
    print(f"[timing] Listening again at {time.strftime('%H:%M:%S')}")
    print("Waiting for 'Hey Jarvis'...")

    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="int16",
        blocksize=FRAME,
    ) as stream:
        while True:
            data, _ = stream.read(FRAME)
            scores = model.predict(np.squeeze(data))
            if scores and max(scores.values()) > THRESHOLD:
                return


def stop_process(process):
    """Shut down the agent and everything it started, right now."""
    subprocess.run(
        ["taskkill", "/PID", str(process.pid), "/T", "/F"],
        capture_output=True,
    )


def run_conversation():
    """Start the LiveKit agent in console mode until it ends or times out."""
    print("Starting conversation...")

    if CLOSE_MARKER.exists():
        CLOSE_MARKER.unlink()

    try:
     
        process = subprocess.Popen(
            ["uv", "run", "src/agent.py", "console"],
            cwd=str(PROJECT_DIR),
        )
    except Exception as e:
        print(f"Could not start Jarvis: {e}")
        return

    started = time.time()
    while process.poll() is None:
        if CLOSE_MARKER.exists():
            print(f"[timing] Conversation ended signal seen after {time.time() - started:.1f}s")
            try:
                kind = CLOSE_MARKER.read_text().strip()
            except Exception:
                kind = "closed"
            if kind == "fast":
                winsound.Beep(660, 120)  # soft chime: dismissed
            else:
                time.sleep(0.5) 
            break
        if time.time() - started > MAX_SESSION_SECONDS:
            print("Conversation time limit reached.")
            break
        time.sleep(0.2)

    stop_started = time.time()
    if process.poll() is None:
        print("[timing] Stopping Jarvis now...")
        stop_process(process)
        process.wait()
    else:
        print("[timing] Jarvis had already closed by itself.")
    print(f"[timing] Stopped after {time.time() - stop_started:.1f}s")

    if CLOSE_MARKER.exists():
        CLOSE_MARKER.unlink()


while True:
    try:
        wait_for_wake_word()
        winsound.Beep(880, 150)
        run_conversation()
        if hasattr(model, "reset"):
            model.reset()
        time.sleep(COOLDOWN_SECONDS)
    except KeyboardInterrupt:
        print("Goodbye.")
        break