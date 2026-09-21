import os
import subprocess
import time

FIFO = "/tmp/protocol7_wtype.fifo"
if not os.path.exists(FIFO):
    os.mkfifo(FIFO)

fd = os.open(FIFO, os.O_RDWR)
with os.fdopen(fd, 'r') as f:
    for line in f:
        if line.strip() == "QUIT_DAEMON":
            break
        # Strip the delimiter: it marks the end of an utterance, and typing it
        # would press Enter into whatever has focus.
        #
        # Do not keep `wtype -` alive and write to its stdin. wtype consumes
        # stdin until EOF before injecting the text, so a long-lived process
        # buffers every dictation indefinitely. Giving each completed FIFO
        # record its own wtype invocation supplies EOF at the end of the
        # utterance and makes the virtual-keyboard events reach the focused
        # application immediately.
        text = line.rstrip("\r\n")
        if text:
            try:
                subprocess.run(["wtype", text], check=True)
            except (OSError, subprocess.CalledProcessError) as error:
                print(f"Protocol7: wtype failed: {error}", flush=True)
