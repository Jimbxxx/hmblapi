from fastapi import APIRouter
from supabase import create_client
from dotenv import load_dotenv
import os
import requests
import jwt
from datetime import datetime, timedelta
from fastapi import Request
from fastapi.responses import RedirectResponse


load_dotenv()

router = APIRouter()

# =========================
# SUPABASE
# =========================
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET")
DISCORD_REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI")
JWT_SECRET = os.getenv("JWT_SECRET")


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
# DEBUG
# =========================
@router.get("/debug-supabase")
def debug():
    return {
        "url": SUPABASE_URL,
        "key_ok": bool(SUPABASE_KEY)
    }

# =========================
# DISCORD LOGIN
# =========================
@router.get("/auth/discord/login")
def discord_login():

    url = (
        "https://discord.com/api/oauth2/authorize"
        f"?client_id={DISCORD_CLIENT_ID}"
        "&response_type=code"
        "&scope=identify"
        f"&redirect_uri={DISCORD_REDIRECT_URI}"
    )

    return RedirectResponse(url)

# =========================
# DISCORD CALLBACK
# =========================
@router.get("/auth/discord/callback")
def discord_callback(code: str):

    try:

        token_data = {
            "client_id": DISCORD_CLIENT_ID,
            "client_secret": DISCORD_CLIENT_SECRET,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": DISCORD_REDIRECT_URI,
            "scope": "identify"
        }

        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }

        token_res = requests.post(
            "https://discord.com/api/oauth2/token",
            data=token_data,
            headers=headers
        )

        token_json = token_res.json()

        access_token = token_json.get("access_token")

        if not access_token:
            return {
                "status": "error",
                "discord_response": token_json
            }

        user_res = requests.get(
            "https://discord.com/api/users/@me",
            headers={
                "Authorization": f"Bearer {access_token}"
            }
        )

        user = user_res.json()

        discord_id = user["id"]
        username_raw = user["username"]
        avatar = user.get("avatar")

        avatar_url = (
            f"https://cdn.discordapp.com/avatars/{discord_id}/{avatar}.png"
            if avatar else None
        )

        existing = supabase.table("players") \
            .select("*") \
            .eq("discord_id", discord_id) \
            .execute()

        if not existing.data:

            hmbl_username = f"{username_raw.lower()}_{discord_id[-4:]}"

            insert = supabase.table("players").insert({
                "discord_id": discord_id,
                "username": hmbl_username,
                "pfp": avatar_url,
                "points": 0,
                "goals": 0,
                "assists": 0,
                "clean_sheets": 0,
                "profile_views": 0,
                "team_id": None,
                "position": None
            }).execute()

            print(insert)

        else:
            hmbl_username = existing.data[0]["username"]

        token = jwt.encode(
            {
                "discord_id": discord_id,
                "username": hmbl_username,
                "exp": datetime.utcnow() + timedelta(days=7)
            },
            JWT_SECRET,
            algorithm="HS256"
        )

        frontend = os.getenv("FRONTEND_URL")

        return RedirectResponse(
            url=f"{frontend}/?token={token}"
        )

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

# =========================
# DISCORD LOGIN CHECK
# =========================
from fastapi import Header, HTTPException

@router.get("/auth/me")
def get_me(authorization: str = Header(None)):

    if not authorization:
        return {"status": "error", "message": "missing token"}

    try:
        token = authorization.replace("Bearer ", "")
        data = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])

        return {
            "status": "success",
            "user": data
        }

    except:
        return {"status": "error", "message": "invalid token"}


# =========================
# UPDATE PROFILE
# =========================
@router.post("/players/update-profile")
def update_profile(payload: dict, authorization: str = Header(None)):

    if not authorization:
        return {"status": "error", "message": "missing token"}

    token = authorization.replace("Bearer ", "")
    data = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])

    discord_id = data["discord_id"]

    username = payload.get("username")
    position = payload.get("position")

    if not username:
        return {"status": "error", "message": "missing username"}

    supabase.table("players").update({
        "username": username,
        "position": position
    }).eq("discord_id", discord_id).execute()

    return {"status": "success"}


# =========================
# GET TEAMS
# =========================
@router.get("/teams")
def get_teams():
    response = supabase.table("teams").select("*").execute()

    teams = {}
    for team in response.data or []:
        teams[str(team["id"])] = team

    return {"status": "success", "data": teams}


# =========================
# GET DIVISIONS
# =========================
@router.get("/divisions")
def get_divisions():
    response = supabase.table("divisions").select("*").execute()

    divisions = {}
    for div in response.data or []:
        divisions[div["name"]] = div

    return {"status": "success", "data": divisions}


# =========================
# GET PLAYERS
# =========================
@router.get("/players")
def get_players():
    response = supabase.table("players").select("*").execute()

    players = {}
    for player in response.data or []:
        players[str(player["id"])] = player

    return {"status": "success", "data": players}


# =========================
# GET MATCHES
# =========================
@router.get("/matches")
def get_matches():
    response = supabase.table("matches").select("*").execute()

    matches = {}
    for match in response.data or []:
        matches[str(match["id"])] = match

    return {"status": "success", "data": matches}


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

    allowed_fields = ["tier", "max_teams", "teams", "current_gameweek", "fixtures"]

    update_data = {}
    for field in allowed_fields:
        if field in data:
            update_data[field] = data[field]

    if not update_data:
        return {"status": "error", "message": "No valid fields"}

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

    team_id = str(insert_res.data[0]["id"])

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

    div_res = supabase.table("divisions").select("*").eq("name", division).execute()

    if div_res.data:
        div = div_res.data[0]
        teams = div.get("teams", [])

        if str(team_id) in teams:
            teams.remove(str(team_id))

        supabase.table("divisions").update({
            "teams": teams
        }).eq("name", division).execute()

    supabase.table("teams").delete().eq("id", team_id).execute()


    return {"status": "success", "message": "Deleted"}
