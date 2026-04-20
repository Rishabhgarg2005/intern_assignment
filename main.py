from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
import re

app = FastAPI(title="Agent Discovery and Usage Platform")

# --- In-Memory Storage ---
agents_db = {}
processed_requests = set()
usage_summary_db = {}

# --- Pydantic Models ---
# FastAPI uses these to automatically handle REQ 3: missing fields/validation
class Agent(BaseModel):
    name: str
    description: str
    endpoint: str

class UsageRequest(BaseModel):
    caller: str
    target: str
    units: int
    request_id: str

# --- Helper Logic for REQ 4: Bonus (Keyword Extraction) ---
def extract_tags(description: str) -> list[str]:
    """Simple keyword extraction (Option B) avoiding complex ML dependencies."""
    stop_words = {"from", "the", "and", "a", "an", "in", "to", "of", "for", "with", "is", "on"}
    # Remove punctuation and split into words
    words = re.findall(r'\b\w+\b', description.lower())
    tags = [word for word in words if not word.isdigit() and word not in stop_words]
    return list(set(tags))  # Return unique tags

# --- REQ 1: Agent Registry APIs ---

@app.post("/agents", status_code=201)
def add_agent(agent: Agent):
    if agent.name in agents_db:
        raise HTTPException(status_code=400, detail="Agent already exists")
    
    # Store agent and auto-generate tags
    agent_data = agent.model_dump()
    agent_data["tags"] = extract_tags(agent.description)
    agents_db[agent.name] = agent_data
    
    # Initialize usage summary for this target
    usage_summary_db[agent.name] = 0
    return {"message": "Agent registered successfully", "agent": agent_data}

@app.get("/agents")
def list_agents():
    return {"agents": list(agents_db.values())}

@app.get("/search")
def search_agents(q: str = Query(..., min_length=1)):
    query = q.lower()
    results = []
    for agent in agents_db.values():
        if query in agent["name"].lower() or query in agent["description"].lower():
            results.append(agent)
    return {"results": results}

# --- REQ 2 & 3: Usage Logging APIs ---

@app.post("/usage")
def log_usage(usage: UsageRequest):
    # REQ 3 Edge Case: logging usage for unknown agent
    if usage.target not in agents_db:
        raise HTTPException(status_code=404, detail="Target agent not found")
    
    # REQ 3 Edge Case & Idempotency: duplicate request_id
    if usage.request_id in processed_requests:
        return {"message": "Usage already logged (duplicate request_id ignored)"}
    
    # Process valid request
    processed_requests.add(usage.request_id)
    usage_summary_db[usage.target] += usage.units
    
    return {"message": "Usage logged successfully", "recorded_units": usage.units}

@app.get("/usage-summary")
def get_usage_summary():
    return usage_summary_db
