from fastapi import FastAPI
from pydantic import BaseModel
from models import SREAction  # Adjust if your action model has a different name
from env import SREEnv        # Adjust if your environment class has a different name

app = FastAPI(title="OpenSRE")
env = SREEnv()

@app.get("/")
def root():
    return {"status": "OpenSRE is running"}

@app.post("/reset")
def reset(task_level: str = "easy"):
    obs = env.reset(task_level=task_level)
    # Convert Pydantic model to dictionary for the JSON response
    return obs.model_dump() if hasattr(obs, "model_dump") else obs

@app.post("/step")
def step(action: SREAction):
    obs, reward, done, info = env.step(action)
    return {
        "observation": obs.model_dump() if hasattr(obs, "model_dump") else obs,
        "reward": reward,
        "done": done
    }