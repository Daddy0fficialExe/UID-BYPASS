import sys
from mitmproxy import http
from mitmproxy.tools.main import mitmdump
import subprocess
import shutil
import os
import socket
import threading


def find_free_port(preferred_port=2012, max_port=2022):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        for port in range(preferred_port, max_port + 1):
            try:
                s.bind(("0.0.0.0", port))
                return port
            except OSError:
                continue
    raise OSError(f"No available port found between {preferred_port} and {max_port}")

def read_output(pipe, prefix):
    """Read output from pipe and print with prefix"""
    try:
        while True:
            line = pipe.readline()
            if not line:
                break
            line = line.rstrip()
            if line:  # Only print non-empty lines
                print(f"[{prefix}] {line}", flush=True)
    except Exception as e:
        print(f"Error reading {prefix} output: {e}", flush=True)
    finally:
        if pipe:
            pipe.close()

if __name__ == "__main__":
    # Start bot.py as a subprocess with unbuffered output
    print("Starting Discord bot...")
    env = os.environ.copy()
    env['PYTHONUNBUFFERED'] = '1'
    bot_process = subprocess.Popen(
        [sys.executable, "-u", "bot.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=os.path.dirname(os.path.abspath(__file__)),
        text=True,
        bufsize=1,
        env=env
    )
    
    # Start threads to read bot output in real-time
    stdout_thread = threading.Thread(target=read_output, args=(bot_process.stdout, "BOT"), daemon=True)
    stderr_thread = threading.Thread(target=read_output, args=(bot_process.stderr, "BOT-ERR"), daemon=True)
    stdout_thread.start()
    stderr_thread.start()
    
    # Start MITMProxy server
    selected_port = find_free_port(2012, 2022)
    if selected_port != 2012:
        print(f"Port 2012 unavailable, using port {selected_port} instead.")

    sys.argv = [
                "mitmdump",
                "-s", "mitmproxyutils.py",
                "-p", str(selected_port),
                "--listen-host", "0.0.0.0",
                "--set", "block_global=false"
            ]
            
    print("Starting MITMProxy server...")
    try:
        mitmdump()
    except KeyboardInterrupt:
        print("\nShutting down...")
        bot_process.terminate()
        bot_process.wait()