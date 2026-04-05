import os
import json
import requests
import time
from openai import OpenAI


API_BASE_URL = os.getenv("API_BASE_URL", "https://api.openai.com/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")
HF_TOKEN = os.getenv("HF_TOKEN")

if HF_TOKEN is None:
    raise ValueError("HF_TOKEN environment variable is required")

# Rule 2: LLM USAGE REQUIREMENTS
client = OpenAI(
    base_url=API_BASE_URL,
    api_key=HF_TOKEN
)

ENV_URL = "http://127.0.0.1:7860"
BENCHMARK_NAME = "OpenSRE"

def parse_action(response_text):
    try:
        start = response_text.find('{')
        end = response_text.rfind('}') + 1
        if start != -1 and end != -1:
            data = json.loads(response_text[start:end])
            return data.get("command", "ls")
    except:
        pass
    return "ls"

def run_evaluation(task_level):
    # Rule 4: [START] format
    print(f"[START] task={task_level} env={BENCHMARK_NAME} model={MODEL_NAME}", flush=True)

    try:
        res = requests.post(f"{ENV_URL}/reset", json={"task_level": task_level}).json()
    except Exception as e:
        print(f"Error connecting to OpenSRE: {e}")
        return

    session_id = res.get("session_id", "default")
    stdout_text = res.get("stdout", "Terminal Ready.")
    
    done = False
    step_count = 0
    history = []
    rewards_history = []
    final_score = 0.0

    while not done and step_count < 15:
        step_count += 1
        
        system_prompt = """You are an autonomous Site Reliability Engineer. 
You must fix the broken web server.
Always output a valid JSON object with two keys:
1. "thought": Your reasoning based on the terminal output.
2. "command": The exact bash command to execute."""

        user_prompt = f"Terminal Output:\n{stdout_text[:1500]}\nPast Commands:\n{history}\nWhat is your next command?"

        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1
            )
            raw_reply = response.choices[0].message.content
            cmd = parse_action(raw_reply)
        except Exception:
            cmd = "ls" 

        history.append(cmd)

        step_res = requests.post(f"{ENV_URL}/step", json={
            "command": cmd, 
            "session_id": session_id
        }).json()
        
        obs = step_res.get("observation", {})
        reward_dict = step_res.get("reward", {})
        done = step_res.get("done", True)
        
        stdout_text = obs.get("stdout", "") + "\n" + obs.get("stderr", "")
        
        # Parse data for Rule 4 formatting
        reward_val = float(reward_dict.get("value", 0.0))
        rewards_history.append(reward_val)
        final_score = reward_val
        
        done_str = "true" if done else "false"
        action_error = obs.get("last_action_error", False)
        error_str = "action_failed" if action_error else "null"
        
        # Rule 4: [STEP] format
        print(f"[STEP] step={step_count} action={cmd} reward={reward_val:.2f} done={done_str} error={error_str}", flush=True)

    # Rule 4: [END] format
    success_str = "true" if final_score >= 1.0 else "false"
    rewards_str = ",".join([f"{r:.2f}" for r in rewards_history])
    print(f"[END] success={success_str} steps={step_count} rewards={rewards_str}", flush=True)

if __name__ == "__main__":
    time.sleep(2)
    for level in ["easy", "medium", "hard"]:
        run_evaluation(level)