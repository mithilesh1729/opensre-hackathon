import os
import subprocess
import shutil
import time
import requests
import platform
import sys
from typing import Literal

try:
    from openenv.core.env_server import Environment
except ImportError:
    try:
        from openenv import Environment
    except ImportError:
        class Environment:
            def __init__(self, *args, **kwargs): pass
            def reset(self, *args, **kwargs): return {}
            def step(self, *args, **kwargs): return {}, 0, True, {}

from models import SREAction, SREObservation, SREReward, SREState

WORKSPACE_DIR = "/tmp/opensre_workspace"

class SREEnv(Environment):
    def __init__(self):
        self._state = None
        self.server_process = None
        self._setup_workspace()

    def _setup_workspace(self):
        """Creates a clean sandbox and securely kills the old server."""
        if self.server_process:
            try:
                self.server_process.terminate()
                self.server_process.wait(timeout=2)
            except: pass
                
        if platform.system() != "Windows":
            subprocess.run("pkill -f flask_app.py", shell=True, capture_output=True)
            subprocess.run("pkill -f zombie.py", shell=True, capture_output=True)
            subprocess.run("pkill -f worker.py", shell=True, capture_output=True)

        time.sleep(1)
        if os.path.exists(WORKSPACE_DIR):
            shutil.rmtree(WORKSPACE_DIR, ignore_errors=True)
        
        os.makedirs(WORKSPACE_DIR, exist_ok=True)
        os.makedirs(os.path.join(WORKSPACE_DIR, "logs"), exist_ok=True)
        os.makedirs(os.path.join(WORKSPACE_DIR, "src"), exist_ok=True)

    def _write_flask_app(self, task_level):
        """Generates the Flask server with the task hardcoded."""
        app_code = f"""from flask import Flask, jsonify
import os
import platform

app = Flask(__name__)

@app.route('/health')
def health():
    task = "{task_level}"
    
    if task == "easy":
        if os.path.exists("logs/error.log") and os.path.getsize("logs/error.log") > 0:
            return jsonify({{"error": "Disk full"}}), 500
        
    if task == "medium":
        try:
            with open("src/config.py") as f:
                if "bad_password" in f.read():
                    return jsonify({{"error": "DB Connection Failed"}}), 500
        except FileNotFoundError:
            return jsonify({{"error": "Config Missing"}}), 500
                    
    if task == "hard":
        if platform.system() == "Windows":
            cmd = 'wmic process get commandline | findstr zombie.py'
        else:
            cmd = 'pgrep -f zombie.py'
        output = os.popen(cmd).read()
        if output.count("zombie.py") > 1: 
            return jsonify({{"error": "Timeout / High CPU"}}), 500
            
    return jsonify({{"status": "ok"}}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
"""
        with open(os.path.join(WORKSPACE_DIR, "flask_app.py"), "w") as f:
            f.write(app_code)

    def reset(self, task_level: Literal["easy", "medium", "hard"] = "easy") -> SREObservation:
        self._setup_workspace()
        self._write_flask_app(task_level)
        
        self._state = SREState(
            task_level=task_level, step_count=0, max_steps=15,
            discovered_log_file=False, identified_rogue_pid=False, 
            server_restarted=False, is_resolved=False, score=0.0
        )

        if task_level == "easy":
            with open(os.path.join(WORKSPACE_DIR, "logs/error.log"), "w") as f:
                f.write("ERROR: OUT OF MEMORY\n" * 5000)
                
        elif task_level == "medium":
            with open(os.path.join(WORKSPACE_DIR, "src/config.py"), "w") as f:
                f.write("DATABASE_URI = 'postgres://user:bad_password@localhost/db'\n")
                
        elif task_level == "hard":
            # UPDATED (Correct)
            for script in ["worker.py", "zombie.py"]:
                # We want Python to insert the actual name 'worker.py', so use single { }
                with open(os.path.join(WORKSPACE_DIR, f"src/{script}"), "w") as f:
                    f.write("import time\nwhile True: time.sleep(1)\n")
                subprocess.Popen([sys.executable, f"src/{script}"], cwd=WORKSPACE_DIR)
        
        # NEW: Write a real restart.sh script so the agent can inspect it
        restart_script = "#!/bin/bash\necho 'Restarting server...'\npkill -f flask_app.py 2>/dev/null || true\nsleep 1\npython3 flask_app.py &\necho 'Server restarted.'\n"
        with open(os.path.join(WORKSPACE_DIR, "restart.sh"), "w") as f:
            f.write(restart_script)
        os.chmod(os.path.join(WORKSPACE_DIR, "restart.sh"), 0o755)

        # Start the server ONLY ONCE
        self.server_process = subprocess.Popen([sys.executable, "flask_app.py"], cwd=WORKSPACE_DIR)
        time.sleep(2)
        return self._get_observation("SSH Login Successful. Type commands to debug.\\n", "", 0, False)

    def step(self, action: SREAction) -> tuple[SREObservation, SREReward, bool, dict]:
        self._state.step_count += 1
        reward_val, reasoning = -0.05, "Standard step penalty."
        cmd = action.command.strip()
        
        if "restart.sh" in cmd:
            if self.server_process: self.server_process.terminate()
            self.server_process = subprocess.Popen([sys.executable, "flask_app.py"], cwd=WORKSPACE_DIR)
            time.sleep(1)
            self._state.server_restarted = True
            stdout, stderr, exit_code, action_error = "Server restarted.\\n", "", 0, False
        else:
            try:
                res = subprocess.run(cmd, shell=True, cwd=WORKSPACE_DIR, timeout=5, capture_output=True, text=True)
                stdout, stderr, exit_code = res.stdout, res.stderr, res.returncode
                action_error = False
            except: stdout, stderr, exit_code, action_error = "", "ERROR", 1, True

        health = 0
        try: health = requests.get("http://localhost:8080/health", timeout=1).status_code
        except: pass

        done = (health == 200 and self._state.server_restarted) or (self._state.step_count >= self._state.max_steps)
        if health == 200 and self._state.server_restarted: reward_val, reasoning = 1.0, "SUCCESS!"
        
        return self._get_observation(stdout, stderr, exit_code, action_error, health), SREReward(value=reward_val, reasoning=reasoning), done, {}

    def _get_observation(self, stdout, stderr, exit_code, error, health=0):
        return SREObservation(stdout=stdout[:1500], stderr=stderr[:1500], exit_code=exit_code, server_health_status=health, last_action_error=error)

    @property
    def state(self) -> SREState: return self._state