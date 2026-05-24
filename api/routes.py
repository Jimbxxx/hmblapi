from fastapi import APIRouter
import json
import os

router = APIRouter()

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data")


# -------------------------
# SAFE JSON LOADER
# -------------------------
def load_json(file):
    path = os.path.join(DATA_PATH, file)

    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception as e:
        return {
            "status": "error",
            "file": file,
            "message": str(e)
        }


# -------------------------
# HOME ROUTE
# -------------------------
@router.get("/")
def home():
    return {
        "name": "HMBL API",
        "status": "online",
        "endpoints": {
            "teams": "/teams",
            "players": "/players",
            "matches": "/matches",
            "divisions": "/divisions"
        }
    }


# -------------------------
# TEAMS
# -------------------------
@router.get("/teams")
def get_teams():
    return {
        "status": "success",
        "data": load_json("teams.json")
    }


# -------------------------
# PLAYERS
# -------------------------
@router.get("/players")
def get_players():
    return {
        "status": "success",
        "data": load_json("players.json")
    }


# -------------------------
# MATCHES
# -------------------------
@router.get("/matches")
def get_matches():
    return {
        "status": "success",
        "data": load_json("matches.json")
    }


# -------------------------
# DIVISIONS
# -------------------------
@router.get("/divisions")
def get_divisions():
    return {
        "status": "success",
        "data": load_json("divisions.json")
    }