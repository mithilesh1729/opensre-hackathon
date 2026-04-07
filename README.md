# OpenSRE: Autonomous DevOps & RL Agent Environment

## 🌍 Environment Description and Motivation (Real-World Utility)
Modern infrastructure debugging is a multi-step, highly contextual process that requires reasoning, exploration, and execution. While many LLM benchmarks focus on static code generation, there is a massive gap in evaluating an agent's ability to operate safely inside a live, broken Linux environment. 

**OpenSRE** fills this gap by providing a containerized, stateless Reinforcement Learning simulation where agents act as Site Reliability Engineers (SREs). The motivation is to evaluate frontier models on genuine, highly practical DevOps tasks—diagnosing port conflicts, hunting memory leaks, and fixing bad configurations—proving their readiness for production-level autonomous operations.

## 📐 Action and Observation Space
The environment uses a strictly typed interface compliant with the Meta OpenEnv spec.

### Action Space
The agent must output a strictly validated JSON object containing the bash command to execute.
- `command` (str): The exact shell command (e.g., `cat logs/error.log`, `pgrep -f zombie.py`).

### Observation Space
The environment parses the terminal execution and returns a dense state representation.
- `stdout` (str): Truncated standard output of the command.
- `stderr` (str): Truncated standard error.
- `exit_code` (int): The bash exit code (0 for success).
- `server_health_status` (int): HTTP status code of the live Flask server (200 = healthy, 500 = broken).
- `last_action_error` (bool): True if the command timed out or failed to execute at the OS level.

## 🎯 Task Descriptions & Expected Difficulty
OpenSRE features a meaningful difficulty progression. To ensure high **Task & Grader Quality**, the environment procedurally injects decoy files and background workers to prevent simple LLM memorization. 

### Easy: The "Disk Full" Outage
- **Objective:** Discover and remove a massive `error.log` file causing an Out of Memory crash, then run `restart.sh`.
- **Mechanics:** Includes dummy `access.log` and `system.log` files to distract the agent.
- **Difficulty:** Low. Tests basic directory traversal and file inspection.

### Medium: Bad Configuration
- **Objective:** Locate a database connection string in `src/config.py`, replace the `bad_password` string using `sed`, and restart the server.
- **Mechanics:** Tests the agent's ability to read code, identify syntax/auth errors, and manipulate file text securely.
- **Difficulty:** Moderate. Requires multi-step reasoning.

### Hard: Rogue Zombie Process
- **Objective:** Identify and kill a rogue `zombie.py` process causing a CPU spike, without killing the actual Flask server or the decoy background workers.
- **Mechanics:** Procedurally spawns harmless `worker_1.py` through `worker_3.py` processes that sleep, masking the actual `zombie.py`.
- **Difficulty:** High. Genuinely challenges frontier models to use tools like `ps`, `pgrep`, and `kill` carefully.

## ⚖️ Grading Logic & Reward Shaping
The environment utilizes a dense, deterministic grading system that mathematically bounds scores between `0.01` and `0.99` (preventing Log-Loss infinity errors during evaluation).
- **Step Penalty:** `-0.05` per action to penalize inefficiency.
- **Anti-Spam Penalty:** Additional `-0.05` if the agent blindly repeats the exact same command.
- **Milestone Rewards:** `+0.20` awarded (locked behind boolean flags to prevent exploit farming) for critical diagnostic steps, like checking the process tree.
- **Efficiency Bonus:** Resolving the server in under 10 steps provides a scaled positive multiplier.

## ⚙️ Setup and Usage Instructions

### 1. Clone and Install
```bash
git clone https://github.com/mithilesh1729/opensre-hackathon.git
cd opensre-hackathon
pip install -r requirements.txt


### 2. Run the Environment Server
The server features UUID session isolation (/step?session_id=...) allowing for parallel automated evaluation without state corruption.

```bash
python server/app.py


### 3. Run the Evaluation
Ensure you have your Hugging Face or OpenAI token exported.

```bash
export HF_TOKEN="your_token_here"
python inference.py


## 📊 Baseline Scores
Evaluated using a baseline ReAct (Reasoning + Acting) loop with `gpt-4o-mini`. 
*(Note: Scores are bounded between 0.01 and 0.99)*

* **Easy Task Avg Score:** 0.99 *(Solved in 4 steps)*
* **Medium Task Avg Score:** 0.89 *(Solved in 6 steps)*
* **Hard Task Avg Score:** 0.65 *(Resolved, but with step penalties)*
* **Overall OpenSRE Benchmark:** 0.84