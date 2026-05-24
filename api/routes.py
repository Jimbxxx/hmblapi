from fastapi import APIRouter
import json
import os

router = APIRouter()

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data")


# =========================
# FILE HELPERS
# =========================
def load_json(file):
    path = os.path.join(DATA_PATH, file)

    try:
        with open(path, "r") as f:
            return json.load(f)
    except:
        return {}


def save_json(file, data):
    path = os.path.join(DATA_PATH, file)

    with open(path, "w") as f:
        json.dump(data, f, indent=4)


# =========================
# HOME
# =========================
@router.get("/")
def home():
    return {
        "name": "HMBL API",
        "status": "online"
    }


# =========================
# GET ENDPOINTS
# =========================
@router.get("/teams")
def get_teams():
    return {"status": "success", "data": load_json("teams.json")}


@router.get("/players")
def get_players():
    return {"status": "success", "data": load_json("players.json")}


@router.get("/matches")
def get_matches():
    return {"status": "success", "data": load_json("matches.json")}


@router.get("/divisions")
def get_divisions():
    return {"status": "success", "data": load_json("divisions.json")}


# =========================
# CREATE DIVISION
# =========================
@router.post("/divisions/create")
def create_division(payload: dict):

    data = load_json("divisions.json")

    name = payload.get("name")
    if not name:
        return {"status": "error", "message": "Missing name"}

    name = name.upper()

    if name in data:
        return {"status": "error", "message": "Division exists"}

    data[name] = {
        "name": name,
        "tier": len(data) + 1,
        "max_teams": 0,
        "teams": [],
        "current_gameweek": 1,
        "fixtures": {}
    }

    save_json("divisions.json", data)

    return {"status": "success", "message": "Division created"}


# =========================
# CREATE TEAM
# =========================
@router.post("/teams/create")
def create_team(payload: dict):

    teams = load_json("teams.json")
    divisions = load_json("divisions.json")

    name = payload.get("name")
    division = payload.get("division")
    manager = payload.get("manager")

    if not all([name, division, manager]):
        return {"status": "error", "message": "Missing fields"}

    team_id = str(len(teams) + 1)

    teams[team_id] = {
        "name": name,
        "division": division,
        "manager": manager,
        "co_managers": [],
        "stats": {
            "played": 0,
            "wins": 0,
            "draws": 0,
            "losses": 0,
            "gf": 0,
            "ga": 0,
            "gd": 0,
            "points": 0
        }
    }

    # attach to division
    if division in divisions:
        divisions[division]["teams"].append(team_id)
        save_json("divisions.json", divisions)

    save_json("teams.json", teams)

    return {"status": "success", "team_id": team_id}


# =========================
# DELETE TEAM
# =========================
@router.post("/teams/delete")
def delete_team(payload: dict):

    teams = load_json("teams.json")
    divisions = load_json("divisions.json")

    team_id = payload.get("team_id")

    if team_id not in teams:
        return {"status": "error", "message": "Not found"}

    team = teams[team_id]

    # remove from division
    div = team.get("division")
    if div in divisions:
        if team_id in divisions[div]["teams"]:
            divisions[div]["teams"].remove(team_id)

    del teams[team_id]

    save_json("teams.json", teams)
    save_json("divisions.json", divisions)

    return {"status": "success", "message": "Deleted"}
