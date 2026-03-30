from fastapi import FastAPI, Body
from pydantic import BaseModel
from typing import Optional

# Safety Imports (Prevents silent crashes if library paths shift)
try:
    from env import SREEnv
    from models import SREAction
except ImportError:
    SREEnv = None
    SREAction = None

app = FastAPI(title="OpenSRE")
env = SREEnv() if SREEnv else None

class ResetRequest(BaseModel):
    task_level: str = "easy"

@app.get("/")
def root():
    return {"status": "OpenSRE is running"}

@app.post("/reset")
def reset(payload: Optional[ResetRequest] = Body(None)):
    if not env:
        return {"error": "Environment not initialized"}
    # Handle empty body by defaulting to "easy"
    level = payload.task_level if payload else "easy"
    obs = env.reset(task_level=level)
    return obs.model_dump() if hasattr(obs, "model_dump") else obs

@app.post("/step")
def step(action: Optional[dict] = Body(None)):
    if not env:
        return {"error": "Environment not initialized"}
    # Flexible action handling
    safe_action = action if action is not None else {}
    obs, reward, done, info = env.step(safe_action)
    return {
        "observation": obs.model_dump() if hasattr(obs, "model_dump") else obs,
        "reward": reward.model_dump() if hasattr(reward, "model_dump") else reward,
        "done": done
    }

@app.get("/state")
def state():
    if not env or not hasattr(env, 'state'):
        return {}
    return env.state.model_dump() if hasattr(env.state, "model_dump") else env.state