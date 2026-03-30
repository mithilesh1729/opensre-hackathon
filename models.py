from pydantic import BaseModel, Field
from typing import Literal

# ============================================================================
# 1. ACTION SPACE: What the LLM can do
# ============================================================================
class SREAction(BaseModel):
    """
    The agent interacts with the server purely through a bash terminal, 
    mimicking a real-world SSH session into a broken server.
    """
    command: str = Field(
        ..., 
        description="The bash command to execute (e.g., 'cat logs/error.log', 'kill -9 1234', 'sed -i s/bad/good/ src/config.py')."
    )

# ============================================================================
# 2. OBSERVATION SPACE: What the LLM sees after acting
# ============================================================================
class SREObservation(BaseModel):
    """
    The output of the executed command, plus a continuous background 
    ping to the server health endpoint to give the agent immediate feedback.
    """
    stdout: str = Field(..., description="Standard output from the executed command.")
    stderr: str = Field(..., description="Standard error from the executed command.")
    exit_code: int = Field(..., description="Exit code of the command (0 typically indicates success).")
    
    # Continuous feedback signal: helps the agent know if it fixed the issue!
    server_health_status: int = Field(
        ..., 
        description="HTTP status code of the local web server (e.g., 200 is healthy, 500 is crashed, 0 means connection refused)."
    )
    last_action_error: bool = Field(
        False, 
        description="True if the action itself failed to execute (e.g., command timed out)."
    )

# ============================================================================
# 3. REWARD SPACE: Dense signals for the RL Loop
# ============================================================================
class SREReward(BaseModel):
    """
    OpenEnv requires a typed Reward model. We use this to provide partial 
    progress signals (dense rewards) rather than just a sparse 0 or 1 at the end.
    """
    value: float = Field(..., description="Reward for this step, range [-1.0, 1.0].")
    reasoning: str = Field(..., description="Explanation of why this reward was given (e.g., '+0.2 for finding the error log').")

# ============================================================================
# 4. STATE SPACE: The Ground Truth (Hidden from the Agent)
# ============================================================================
class SREState(BaseModel):
    """
    Internal state of the environment. Used by the reset() and state() API methods,
    and highly crucial for our deterministic Grader functions.
    """
    task_level: Literal["easy", "medium", "hard"] = Field(..., description="Current difficulty tier.")
    step_count: int = Field(0, description="Number of actions taken so far.")
    max_steps: int = Field(15, description="Maximum allowed steps before episode termination.")
    
    # Trackers for Reward Shaping (So we only reward them ONCE for a discovery)
    discovered_log_file: bool = Field(False, description="Did the agent read the error log?")
    identified_rogue_pid: bool = Field(False, description="Did the agent run top/ps to find the zombie process?")
    server_restarted: bool = Field(False, description="Did the agent run the restart script?")
    
    # Final Grader Check
    is_resolved: bool = Field(False, description="True if the GET /health check returns 200 OK.")
    score: float = Field(0.0, description="Cumulative score for the episode (0.0 to 1.0).")