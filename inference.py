import os
import json
from openai import OpenAI
from env import SREEnv
from models import SREAction

# MANDATORY HACKATHON VARIABLES
API_BASE_URL = os.getenv("API_BASE_URL", "https://api.openai.com/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")
HF_TOKEN = os.getenv("HF_TOKEN")

client = OpenAI(
    base_url=API_BASE_URL,
    api_key=HF_TOKEN or "dummy_key_for_local_testing",
)

SYSTEM_PROMPT = """You are debugging a simulated server inside a restricted workspace.

IMPORTANT RULES:
- You are NOT in a real global Linux system.
- DO NOT use /var/log, apt-get, sudo, or dpkg.
- All files are inside the current local directory.
- Logs are in: logs/error.log
- Config is in: src/config.py
- To apply fixes, you MUST restart the server using: bash restart.sh

EXAMPLES OF VALID COMMANDS:
ls -la
cat logs/error.log
rm logs/error.log
ps aux
pkill -f zombie.py
sed -i 's/bad_password/good_password/g' src/config.py
bash restart.sh

You MUST respond ONLY with valid JSON matching this schema. Do not add markdown or explanations.
{"command": "your_bash_command_here"}"""

def parse_model_action(response_text: str) -> str:
    """Safely extracts the bash command."""
    try:
        clean_text = response_text.replace("```json", "").replace("```", "").strip()
        start = clean_text.find('{')
        end = clean_text.rfind('}') + 1
        if start != -1 and end != -1:
            clean_text = clean_text[start:end]
        parsed = json.loads(clean_text)
        return parsed.get("command", "echo 'JSON Parse Error'")
    except Exception:
        print(f"[!] JSON Parse Error on raw text: {response_text}")
        return "echo 'LLM output was not valid JSON'"

def run_task(env: SREEnv, task_level: str):
    print(f"\n{'='*50}\n🚀 STARTING TASK: {task_level.upper()}\n{'='*50}")
    obs = env.reset(task_level=task_level)
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Initial Login STDOUT:\n{obs.stdout}"}
    ]

    done = False
    step = 0

    while not done:
        step += 1
        
        try:
            completion = client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                temperature=0.1, 
                max_tokens=150,
            )
            response_text = completion.choices[0].message.content or ""
        except Exception as exc:
            # FIXED: Safe fallback without crashing the environment
            print(f"API Error: {exc}")
            response_text = '{"command": "ls"}'

        command_str = parse_model_action(response_text)
        print(f"Step {step} | Agent ➡️  {command_str}")
        
        obs, reward, done, _ = env.step(SREAction(command=command_str))
        
        status_color = "🟢 OK" if obs.server_health_status == 200 else "🔴 DOWN"
        print(f"  ↳ Reward: {reward.value:+.2f} | Health: {obs.server_health_status} {status_color} | Reason: {reward.reasoning}")

        messages.append({"role": "assistant", "content": response_text})
        obs_text = f"STDOUT:\n{obs.stdout[:500]}\nSTDERR:\n{obs.stderr[:500]}\nEXIT CODE: {obs.exit_code}\nHEALTH: {obs.server_health_status}"
        messages.append({"role": "user", "content": obs_text})

    print(f"🏁 Task '{task_level}' Complete. Final Score: {env.state.score}/1.0")
    return env.state.score

if __name__ == "__main__":
    env = SREEnv()
    tasks = ["easy", "medium", "hard"]
    scores = {}
    
    for task in tasks:
        scores[task] = run_task(env, task)
        
    print("\n" + "="*50)
    print("🏆 OPEN SRE BASELINE EVALUATION COMPLETE")
    for t, s in scores.items():
        print(f" - {t.capitalize()}: {s}/1.0")
    print("="*50)