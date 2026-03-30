# server/app.py
from fastapi import FastAPI, Body
from pydantic import BaseModel
from typing import Optional
import sys
import os

# This line is CRITICAL so the app can find env.py and models.py at the root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from env import SREEnv
from models import SREAction

app = FastAPI(title="OpenSRE")
env = SREEnv()

class ResetRequest(BaseModel):
    task_level: str = "easy"

@app.get("/")
def root():
    return {"status": "OpenSRE is running"}

@app.post("/reset")
def reset(payload: Optional[ResetRequest] = Body(None)):
    level = payload.task_level if payload else "easy"
    obs = env.reset(task_level=level)
    return obs.model_dump()

@app.post("/step")
def step(action: SREAction):
    obs, reward, done, _ = env.step(action)
    return {
        "observation": obs.model_dump(), 
        "reward": reward.model_dump(), 
        "done": done
    }