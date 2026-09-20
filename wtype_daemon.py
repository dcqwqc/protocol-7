import os
import subprocess
import time

FIFO = "/tmp/protocol7_wtype.fifo"
if not os.path.exists(FIFO):
    os.mkfifo(FIFO)

proc = subprocess.Popen(["wtype", "-"], stdin=subprocess.PIPE, text=True, bufsize=0)
fd = os.open(FIFO, os.O_RDWR)
with os.fdopen(fd, 'r') as f:
    for line in f:
        if line.strip() == "QUIT_DAEMON":
            break
        proc.stdin.write(line)
        proc.stdin.flush()
proc.terminate()
