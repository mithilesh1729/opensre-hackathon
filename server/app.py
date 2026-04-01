from fastapi import FastAPI, Body, Request
from pydantic import BaseModel
from typing import Optional, Dict
from uuid import uuid4
import sys
import os
import uvicorn

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from env import SREEnv
    from models import SREAction
except ImportError:
    SREEnv = None
    SREAction = None

app = FastAPI(title="OpenSRE")

# NEW: Session dictionary for parallel grading
sessions: Dict[str, SREEnv] = {}
# Fallback for inference.py if it doesn't use sessions
DEFAULT_SESSION_ID = "default"
if SREEnv:
    sessions[DEFAULT_SESSION_ID] = SREEnv()

class ResetRequest(BaseModel):
    task_level: str = "easy"

@app.get("/")
def root():
    return {"status": "OpenSRE is running"}

@app.get("/health")
def health():
    return {"status": "healthy", "environment": "OpenSRE", "version": "2.0.0"}

@app.post("/reset")
def reset(payload: Optional[ResetRequest] = Body(None)):
    if not SREEnv:
        return {"error": "Environment not initialized"}
    
    # NEW: Generate a unique session for this specific reset
    session_id = str(uuid4())
    env = SREEnv()
    sessions[session_id] = env
    
    level = payload.task_level if payload else "easy"
    obs = env.reset(task_level=level)
    
    response_data = obs.model_dump() if hasattr(obs, "model_dump") else obs
    response_data["session_id"] = session_id  # Pass it back to the grader
    return response_data

@app.post("/step")
def step(action_dict: Optional[dict] = Body(None)):
    # Safely extract session_id or fallback to default
    session_id = action_dict.get("session_id", DEFAULT_SESSION_ID) if action_dict else DEFAULT_SESSION_ID
    env = sessions.get(session_id, sessions.get(DEFAULT_SESSION_ID))
    
    if not env:
        return {"error": "Environment not initialized"}
        
    safe_dict = action_dict if action_dict is not None else {"command": "ls"}
    # Remove session_id before passing to SREAction to avoid validation errors
    safe_dict.pop("session_id", None) 
    
    action_obj = SREAction(**safe_dict)
    obs, reward, done, info = env.step(action_obj)
    
    return {
        "observation": obs.model_dump() if hasattr(obs, "model_dump") else obs,
        "reward": reward.model_dump() if hasattr(reward, "model_dump") else reward,
        "done": bool(done)
    }

def main():
    uvicorn.run("server.app:app", host="0.0.0.0", port=7860, reload=False)

if __name__ == "__main__":
    main()