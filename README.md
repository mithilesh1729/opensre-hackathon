---
title: OpenSRE Hackathon
emoji: 🚀
colorFrom: blue
colorTo: green
sdk: docker
pinned: false
short_description: 'About OpenSRE: AI-Powered Server Debugging Environment'
---
# OpenSRE: Autonomous DevOps & SRE Environment

## 📖 Description & Motivation
OpenSRE is a high-fidelity, real-world Site Reliability Engineering (SRE) simulation environment built for the Meta OpenEnv standard. Modern AI agents struggle with live server debugging because it requires exploring an opaque system, reading logs, and safely executing destructive commands (like `kill` or `rm`). 

OpenSRE dynamically spins up a containerized Linux workspace and a live Flask server (`http://localhost:8080`). The agent is given an SSH-like terminal and must diagnose and resolve production-grade infrastructure failures.

## 🛠 Action and Observation Spaces

**Action Space:**
The agent issues raw bash commands via the `SREAction` model. 
* `command` (str): Any valid bash command (e.g., `cat logs/error.log`, `ps aux`, `bash restart.sh`).

**Observation Space (`SREObservation`):**
* `stdout` (str): The standard output of the executed bash command.
* `stderr` (str): Any error output from the shell.
* `exit_code` (int): The shell return code.
* `server_health_status` (int): The HTTP status code of the underlying web server (200 OK means resolved).

## 🚀 Tasks & Difficulty Progression
OpenSRE features 3 procedurally injected scenarios alongside benign "decoy" files and processes to prevent LLM memorization.

1.  **Easy (Disk Full):** A massive `error.log` is causing the server to crash. The agent must find it among decoy logs and delete it.
2.  **Medium (Bad Configuration):** The database connection string in `src/config.py` contains a typo (`bad_password`). The agent must use tools like `sed` to fix the file.
3.  **Hard (Rogue Zombie Process):** A `zombie.py` process is hogging CPU resources. The agent must use `ps` or `pgrep`, identify the correct PID amongst healthy background workers, `kill` it, and restart the server.

## 🏆 Reward Shaping (Grader Logic)
OpenSRE uses an advanced, deterministic Dense Reward system:
* **Success:** Agent achieves HTTP 200 on the `/health` endpoint (+1.0).
* **Efficiency Bonus:** Bonus points awarded if the agent solves the task in under 10 steps.
* **Milestone Rewards:** +0.20 for correct diagnostic steps (e.g., reading logs, checking process trees).
* **Penalties:** -0.05 step penalty, and additional penalties for spamming identical commands.

## ⚙️ Setup & Usage

**1. Install Dependencies:**
```bash
pip install -r requirements.txt
pip install openenv-core


2. Run the Baseline Evaluation:
Ensure you have exported your API credentials as per the OpenEnv spec:

Bash
export MODEL_NAME="gpt-4o-mini"
export HF_TOKEN="your_openai_api_key_here"
python3 inference.py
📊 Baseline Scores (GPT-4o-mini)
Easy: 1.0 / 1.0

Medium: 0.95 / 1.0 (Average)

Hard: 0.85 / 1.0 (Average - occasionally struggles with complex sed syntax)