import os
import json
import requests
import time
from openai import OpenAI

# ==========================================
# 1. PRE-SUBMISSION CHECKLIST: ENVIRONMENT VARIABLES
# ==========================================
API_BASE_URL = os.environ.get("API_BASE_URL", "https://api.openai.com/v1")
MODEL_NAME = os.environ.get("MODEL_NAME", "gpt-4o-mini")
HF_TOKEN = os.environ.get("HF_TOKEN", os.environ.get("OPENAI_API_KEY", ""))

# ==========================================
# 2. PRE-SUBMISSION CHECKLIST: OPENAI CLIENT
# ==========================================
client = OpenAI(
    base_url=API_BASE_URL,
    api_key=HF_TOKEN if HF_TOKEN else "dummy-key-for-local"
)

# Configuration for your OpenSRE 2.0 Environment
ENV_URL = "http://127.0.0.1:7860"

def parse_action(response_text):
    """Extracts the bash command from the LLM's JSON output."""
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
    """Runs a single episode and strictly formats the output logs."""
    
    # ==========================================
    # 3. PRE-SUBMISSION CHECKLIST: [START] LOG
    # ==========================================
    print(f"[START] Task: {task_level}")

    # Initialize environment and get session
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
    final_score = 0.0

    while not done and step_count < 15:
        step_count += 1
        
        # True "Smart Agent" ReAct Prompt
        system_prompt = """You are an autonomous Site Reliability Engineer. 
You must fix the broken web server.
Always output a valid JSON object with two keys:
1. "thought": Your reasoning based on the terminal output.
2. "command": The exact bash command to execute."""

        user_prompt = f"Terminal Output:\n{stdout_text[:1500]}\nPast Commands:\n{history}\nWhat is your next command?"

        # LLM Call
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
        except Exception as e:
            cmd = "ls" # Fallback if API quota fails

        history.append(cmd)

        # ==========================================
        # 4. PRE-SUBMISSION CHECKLIST: [STEP] LOG
        # ==========================================
        print(f"[STEP] {step_count} | {cmd}")

        # Execute in Sandbox
        step_res = requests.post(f"{ENV_URL}/step", json={
            "command": cmd, 
            "session_id": session_id
        }).json()
        
        obs = step_res.get("observation", {})
        reward = step_res.get("reward", {})
        done = step_res.get("done", True)
        
        stdout_text = obs.get("stdout", "") + "\n" + obs.get("stderr", "")
        
        # In case the episode finishes, grab the latest score
        # Note: If you want to fetch the exact score, you might need a /state endpoint
        # For logging purposes, we'll track the last reward value.
        final_score = reward.get("value", 0.0)

    # ==========================================
    # 5. PRE-SUBMISSION CHECKLIST: [END] LOG
    # ==========================================
    print(f"[END] Task: {task_level} | Final Score: {final_score}")

if __name__ == "__main__":
    # Give the FastAPI server a second to boot if starting concurrently
    time.sleep(2)
    
    for level in ["easy", "medium", "hard"]:
        run_evaluation(level)
        print("-" * 40)