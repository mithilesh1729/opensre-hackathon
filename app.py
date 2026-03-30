from fastapi import FastAPI, Body
from pydantic import BaseModel
from typing import Optional

# Safety Imports
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
def step(action_dict: Optional[dict] = Body(None)):
    if not env:
        return {"error": "Environment not initialized"}
    
    # 1. Convert the dictionary from the API into an SREAction object
    # This is the "Bridge" that prevents the AttributeError
    safe_dict = action_dict if action_dict is not None else {"command": "ls"}
    action_obj = SREAction(**safe_dict)
    
    # 2. Pass the object to env.py
    obs, reward, done, info = env.step(action_obj)
    
    return {
        "observation": obs.model_dump() if hasattr(obs, "model_dump") else obs,
        "reward": reward.model_dump() if hasattr(reward, "model_dump") else reward,
        "done": bool(done)
    }

@app.get("/state")
def state():
    if not env or not hasattr(env, 'state'):
        return {}
    return env.state.model_dump() if hasattr(env.state, "model_dump") else env.state