from fastapi import FastAPI, Body
from pydantic import BaseModel
from typing import Optional
import os

# 1. Safety Import: Try the library path first, then fall back to a stub
try:
    from openenv.core.env_server import Environment
    from env import SREEnv
    from models import SREAction
except ImportError:
    # This prevents the whole server from crashing if the library path shifts
    class Environment: pass
    SREEnv = None
    SREAction = None

app = FastAPI(title="OpenSRE")
env = SREEnv() if SREEnv else None

# This model tells FastAPI to look for JSON in the request body
class ResetRequest(BaseModel):
    task_level: str = "easy"

@app.get("/")
def root():
    return {"status": "OpenSRE is running", "ready": env is not None}

@app.post("/reset")
def reset(payload: ResetRequest = Body(...)):
    if not env:
        return {"error": "Environment not initialized"}
    
    # This handles both task_level in JSON body and defaults
    obs = env.reset(task_level=payload.task_level)
    return obs.model_dump() if hasattr(obs, "model_dump") else obs

@app.post("/step")
def step(action: dict = Body(...)):
    if not env:
        return {"error": "Environment not initialized"}
    
    # We use a dict here for maximum flexibility with the grader's JSON
    obs, reward, done, info = env.step(action)
    return {
        "observation": obs.model_dump() if hasattr(obs, "model_dump") else obs,
        "reward": reward,
        "done": done
    }