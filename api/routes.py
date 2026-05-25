from fastapi import APIRouter
from supabase import create_client
from dotenv import load_dotenv
import os

load_dotenv()

router = APIRouter()

# =========================
# SUPABASE
# =========================
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


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
# GET TEAMS
# =========================
@router.get("/teams")
def get_teams():
    response = supabase.table("teams").select("*").execute()

    teams = {}

    for team in response.data or []:
        teams[str(team["id"])] = team

    return {
        "status": "success",
        "data": teams
    }


# =========================
# GET DIVISIONS
# =========================
@router.get("/divisions")
def get_divisions():
    response = supabase.table("divisions").select("*").execute()

    divisions = {}

    for div in response.data or []:
        divisions[div["name"]] = div

    return {
        "status": "success",
        "data": divisions
    }


# =========================
# GET PLAYERS
# =========================
@router.get("/players")
def get_players():
    response = supabase.table("players").select("*").execute()

    players = {}

    for player in response.data or []:
        players[str(player["id"])] = player

    return {
        "status": "success",
        "data": players
    }


# =========================
# GET MATCHES
# =========================
@router.get("/matches")
def get_matches():
    response = supabase.table("matches").select("*").execute()

    matches = {}

    for match in response.data or []:
        matches[str(match["id"])] = match

    return {
        "status": "success",
        "data": matches
    }


# =========================
# CREATE DIVISION
# =========================
@router.post("/divisions/create")
def create_division(payload: dict):

    name = payload.get("name")
    max_teams = payload.get("max_teams", 0)

    if not name:
        return {"status": "error", "message": "Missing name"}

    name = name.upper()

    existing = supabase.table("divisions").select("name").eq("name", name).execute()

    if existing.data:
        return {"status": "error", "message": "Division exists"}

    all_divs = supabase.table("divisions").select("name").execute().data or []
    tier = len(all_divs) + 1

    supabase.table("divisions").insert({
        "name": name,
        "tier": tier,
        "max_teams": max_teams,
        "teams": [],
        "current_gameweek": 1,
        "fixtures": {}
    }).execute()

    return {"status": "success", "message": "Division created"}


# =========================
# DELETE DIVISION
# =========================
@router.post("/divisions/delete")
def delete_division(payload: dict):

    name = payload.get("name")

    if not name:
        return {"status": "error", "message": "Missing name"}

    name = name.upper()

    existing = supabase.table("divisions").select("name").eq("name", name).execute()

    if not existing.data:
        return {"status": "error", "message": "Not found"}

    supabase.table("divisions").delete().eq("name", name).execute()

    return {"status": "success", "message": "Deleted"}


# =========================
# UPDATE DIVISION (SAFE)
# =========================
@router.post("/divisions/update")
def update_division(payload: dict):

    name = payload.get("division")
    data = payload.get("data")

    if not name or not data:
        return {"status": "error", "message": "Missing fields"}

    name = name.upper()

    # SAFE FIELD UPDATE ONLY (prevents overwriting entire row incorrectly)
    update_data = {}

    allowed_fields = [
        "tier",
        "max_teams",
        "teams",
        "current_gameweek",
        "fixtures"
    ]

    for field in allowed_fields:
        if field in data:
            update_data[field] = data[field]

    supabase.table("divisions").update(update_data).eq("name", name).execute()

    return {"status": "success", "message": "Updated"}


# =========================
# CREATE TEAM
# =========================
@router.post("/teams/create")
def create_team(payload: dict):

    name = payload.get("name")
    division = payload.get("division")
    manager = payload.get("manager")
    color = payload.get("color", 0xf39c12)

    if not all([name, division, manager]):
        return {"status": "error", "message": "Missing fields"}

    division = division.upper()

    insert_res = supabase.table("teams").insert({
        "name": name,
        "division": division,
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
    }).execute()

    if not insert_res.data:
        return {"status": "error", "message": "Insert failed"}

    created_team = insert_res.data[0]
    team_id = str(created_team["id"])

    # attach to division
    div_res = supabase.table("divisions").select("*").eq("name", division).execute()

    if div_res.data:
        div = div_res.data[0]

        teams = div.get("teams", [])

        if team_id not in teams:
            teams.append(team_id)

        supabase.table("divisions").update({
            "teams": teams
        }).eq("name", division).execute()

    return {"status": "success", "team_id": team_id}


# =========================
# DELETE TEAM
# =========================
@router.post("/teams/delete")
def delete_team(payload: dict):

    team_id = payload.get("team_id")

    if not team_id:
        return {"status": "error", "message": "Missing team_id"}

    team_res = supabase.table("teams").select("*").eq("id", team_id).execute()

    if not team_res.data:
        return {"status": "error", "message": "Not found"}

    team = team_res.data[0]
    division = team["division"].upper()

    # remove from division
    div_res = supabase.table("divisions").select("*").eq("name", division).execute()

    if div_res.data:
        div = div_res.data[0]

        teams = div.get("teams", [])

        if str(team_id) in teams:
            teams.remove(str(team_id))

        supabase.table("divisions").update({
            "teams": teams
        }).eq("name", division).execute()

    # delete team
    supabase.table("teams").delete().eq("id", team_id).execute()

    return {"status": "success", "message": "Deleted"}
