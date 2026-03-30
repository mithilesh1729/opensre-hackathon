---
title: OpenSRE Hackathon
emoji: 🚀
colorFrom: blue
colorTo: green
sdk: docker
pinned: false
---

# 🛠️ OpenSRE: Autonomous DevOps Environment

## 🚀 What Problem Does This Solve?
This environment evaluates whether AI agents can autonomously diagnose and fix real-world server failures, mimicking the exact workflow and constraints of a human DevOps engineer.

**OpenSRE** is a production-grade Reinforcement Learning environment built for the Meta OpenEnv Hackathon. It evaluates an AI agent's ability to act as a Site Reliability Engineer (SRE) by troubleshooting, fixing, and restarting a broken web server via a safe, simulated Bash terminal.

## 🌟 Why OpenSRE? (Real-World Utility)
Instead of toy games, OpenSRE simulates the exact multi-step reasoning required in enterprise DevOps:
1. **Diagnosis:** Navigating file systems, reading logs, and inspecting process trees (`ps`, `top`).
2. **Resolution:** Modifying config files or killing rogue background processes.
3. **Validation:** Explicitly restarting the service (`./restart.sh`) to achieve a 200 OK health check.

## 🎯 Task Progression
* **Easy:** Disk Full Simulation. The server is crashing due to an oversized error log.
* **Medium:** Bad Config. The database connection string contains a typo preventing boot.
* **Hard:** Zombie Process. Multiple decoy processes run, but one specific zombie is starving the CPU. Agent must identify and `kill -9` the correct PID.

## 🧠 Advanced RL Reward Shaping
This environment goes beyond sparse binary rewards. It features anti-exploitation logic:
* **Dense Exploration Signals:** +0.05 for exploring (`ls`, `cd`).
* **Milestone Rewards:** +0.2 for successfully finding and reading the correct error log.
* **Anti-Farming Penalties:** -0.02 if the agent repeatedly cats the same log file after discovering it.
* **Destructive Penalties:** -0.5 for using `rm -rf` or crashing the execution sandbox.

## 🚀 Running the Baseline
Ensure you have set `HF_TOKEN`, `API_BASE_URL`, and `MODEL_NAME`.
```bash
python3 inference.py
```