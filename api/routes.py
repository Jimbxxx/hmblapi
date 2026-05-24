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
# HEALTH CHECK
# =========================
@router.get("/")
def home():
    return {
        "name": "HMBL API",
        "status": "online"
    }


# =========================
# GET DATA
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
# DIVISIONS
# =========================
@router.post("/divisions/create")
def create_division(payload: dict):

    data = load_json("divisions.json")

    name = payload.get("name")
    max_teams = payload.get("max_teams", 0)

    if not name:
        return {"status": "error", "message": "Missing name"}

    name = name.upper()

    if name in data:
        return {"status": "error", "message": "Division exists"}

    data[name] = {
        "name": name,
        "tier": len(data) + 1,
        "max_teams": max_teams,
        "teams": [],
        "current_gameweek": 1,
        "fixtures": {}
    }

    save_json("divisions.json", data)

    return {"status": "success", "message": "Division created"}


@router.post("/divisions/delete")
def delete_division(payload: dict):

    data = load_json("divisions.json")

    name = payload.get("name")
    if not name:
        return {"status": "error", "message": "Missing name"}

    name = name.upper()

    if name not in data:
        return {"status": "error", "message": "Not found"}

    del data[name]

    save_json("divisions.json", data)

    return {"status": "success", "message": "Deleted"}


@router.post("/divisions/update")
def update_division(payload: dict):

    data = load_json("divisions.json")

    name = payload.get("division")
    new_data = payload.get("data")

    if not name or not new_data:
        return {"status": "error", "message": "Missing fields"}

    name = name.upper()

    data[name] = new_data

    save_json("divisions.json", data)

    return {"status": "success", "message": "Updated"}


# =========================
# TEAMS
# =========================
@router.post("/teams/create")
def create_team(payload: dict):

    teams = load_json("teams.json")
    divisions = load_json("divisions.json")

    name = payload.get("name")
    division = payload.get("division")
    manager = payload.get("manager")

    color = payload.get("color", 0xf39c12)

    if not all([name, division, manager]):
        return {"status": "error", "message": "Missing fields"}

    team_id = str(int(max(teams.keys(), default="0")) + 1)

    teams[team_id] = {
        "name": name,
        "division": division.upper(),
        "manager": manager,
        "co_managers": [],
        "color": color,
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

    # attach to division safely
    div_name = division.upper()
    if div_name in divisions:
        divisions[div_name].setdefault("teams", [])
        if team_id not in divisions[div_name]["teams"]:
            divisions[div_name]["teams"].append(team_id)

    save_json("teams.json", teams)
    save_json("divisions.json", divisions)

    return {"status": "success", "team_id": team_id}


@router.post("/teams/delete")
def delete_team(payload: dict):

    teams = load_json("teams.json")
    divisions = load_json("divisions.json")

    team_id = payload.get("team_id")

    if not team_id or team_id not in teams:
        return {"status": "error", "message": "Not found"}

    team = teams[team_id]

    div_name = team.get("division", "").upper()

    if div_name in divisions:
        if team_id in divisions[div_name].get("teams", []):
            divisions[div_name]["teams"].remove(team_id)

    del teams[team_id]

    save_json("teams.json", teams)
    save_json("divisions.json", divisions)

    return {"status": "success", "message": "Deleted"}
