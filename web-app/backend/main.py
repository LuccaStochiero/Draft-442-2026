from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import os
from draft_engine import DraftEngine

app = FastAPI()

# Enable CORS for Next.js
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Engine
DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "Players.csv")
engine = DraftEngine(DATA_PATH)

# --- Pydantic Models ---
class TeamSetup(BaseModel):
    name: str
    logo: str = "" # Base64

class SetupRequest(BaseModel):
    league_name: str
    teams: List[TeamSetup] 
    n_rounds: int = 10
    random_order: bool = False # Default to False per user request

class PickRequest(BaseModel):
    team_idx: int
    player_name: str

# --- Endpoints ---

@app.get("/")
def read_root():
    return {"message": "Fantasy Draft API Running", "setup": engine.is_setup}

@app.post("/api/reset")
def reset_draft():
    return engine.reset_league()

@app.post("/api/setup")
def setup_draft(req: SetupRequest):
    try:
        # Convert Pydantic models to dicts for engine
        teams_data = [t.dict() for t in req.teams]
        state = engine.setup_league(req.league_name, teams_data, req.n_rounds, req.random_order)
        return state
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/state")
def get_state():
    return engine.get_state()

@app.get("/api/players")
def get_available_players():
    return engine.get_available_players()

@app.post("/api/pick")
def make_pick(req: PickRequest):
    try:
        state = engine.make_pick(req.team_idx, req.player_name)
        return state
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/undo")
def undo_pick():
    try:
        state = engine.undo_last_pick()
        return state
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/export")
def export_csv():
    csv_content = engine.export_results_csv()
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=draft_results.csv"}
    )
