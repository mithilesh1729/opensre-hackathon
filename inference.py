import os
import json
import requests
import time
from openai import OpenAI
import httpx

API_BASE_URL = os.getenv("API_BASE_URL", "https://api.openai.com/v1")
MODEL_NAME   = os.getenv("MODEL_NAME", "gpt-4o-mini")
API_KEY      = os.getenv("HF_TOKEN") or os.getenv("OPENAI_API_KEY", "dummy_key")

# The crucial fix: explicitly instantiate the httpx client to bypass the proxies bug
custom_http_client = httpx.Client()

client = OpenAI(
    base_url=API_BASE_URL, 
    api_key=API_KEY,
    http_client=custom_http_client
)

ENV_URL        = "http://127.0.0.1:7860"
BENCHMARK_NAME = "OpenSRE"
MAX_STEPS      = 15

def parse_action(text):
    try:
        start = text.find('{')
        end   = text.rfind('}') + 1
        if start != -1 and end > start:
            return json.loads(text[start:end]).get("command", "ls")
    except Exception:
        pass
    return "ls"

def run_evaluation(task_level):
    print(f"[START] task={task_level} env={BENCHMARK_NAME} model={MODEL_NAME}", flush=True)

    step_count    = 0
    rewards_list  = []
    is_resolved   = False

    try:
        try:
            res = requests.post(
                f"{ENV_URL}/reset",
                json={"task_level": task_level},
                timeout=30
            ).json()
        except Exception as e:
            print(f"[DEBUG] reset failed: {e}", flush=True)
            return 0.0

        session_id = res.get("session_id", "default")
        stdout_text = res.get("stdout", "Terminal Ready.")
        done = False

        system_prompt = """You are an autonomous SRE fixing a broken web server in a sandbox.
Output ONLY valid JSON: {"command": "your_bash_command"}
Valid commands: ls -la, cat logs/error.log, rm logs/error.log,
ps aux, pgrep -f zombie.py, kill -9 <PID>,
sed -i 's/bad_password/good_password/g' src/config.py, bash restart.sh"""

        while not done and step_count < MAX_STEPS:
            step_count += 1

            user_prompt = (
                f"Terminal Output:\n{stdout_text[:1000]}\n"
                f"Step: {step_count}/{MAX_STEPS}\n"
                f"Issue: bash restart.sh after any fix to apply it."
            )

            try:
                response = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user",   "content": user_prompt},
                    ],
                    temperature=0.1,
                    max_tokens=150,
                )
                cmd = parse_action(response.choices[0].message.content or "")
            except Exception as exc:
                print(json.dumps({"event": "DEBUG", "msg": str(exc)}), flush=True)
                cmd = "ls"

            try:
                # CRITICAL FIX: session_id goes as query param, action as body
                step_res = requests.post(
                    f"{ENV_URL}/step",
                    params={"session_id": session_id},
                    json={"command": cmd},
                    timeout=30
                ).json()
            except Exception as exc:
                print(json.dumps({"event": "DEBUG", "msg": str(exc)}), flush=True)
                break # Exit the loop if the step fails

            obs         = step_res.get("observation", {})
            reward_dict = step_res.get("reward", {})
            done        = step_res.get("done", True)
            reward_val  = float(reward_dict.get("value", 0.0))

            rewards_list.append(reward_val)
            stdout_text  = obs.get("stdout", "") + "\n" + obs.get("stderr", "")
            is_resolved  = obs.get("server_health_status", 0) == 200
            action_error = obs.get("last_action_error", False)
            error_str    = "action_failed" if action_error else "null"

            print(
                f"[STEP] step={step_count} action={cmd} "
                f"reward={reward_val:.2f} done={'true' if done else 'false'} "
                f"error={error_str}",
                flush=True
            )

    finally:
        # Guarantee [END] log is printed
        total_possible = 1.0 + 0.2 + 0.15  # max rewards in env
        raw_sum        = sum(rewards_list)
        score          = round(min(max(raw_sum / total_possible, 0.0), 1.0), 4)
        success_str    = "true" if is_resolved else "false"
        rewards_str    = ",".join(f"{r:.2f}" for r in rewards_list) if rewards_list else "0.00"

        print(
            f"[END] success={success_str} steps={step_count} "
            f"score={score} rewards={rewards_str}",
            flush=True
        )

    return score

if __name__ == "__main__":
    time.sleep(3)  # wait for uvicorn to be fully ready
    total = 0.0
    for level in ["easy", "medium", "hard"]:
        total += run_evaluation(level)
    print(f"[SUMMARY] avg_score={round(total/3, 4)}", flush=True)