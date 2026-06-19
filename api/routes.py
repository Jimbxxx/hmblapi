from fastapi import APIRouter, Header
from supabase import create_client
from dotenv import load_dotenv
import os
import requests
import jwt
from datetime import datetime, timedelta
from fastapi.responses import RedirectResponse
import base64

load_dotenv()

router = APIRouter()

# =========================
# ENV
# =========================
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET")
DISCORD_REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI")
JWT_SECRET = os.getenv("JWT_SECRET")
FRONTEND_URL = os.getenv("FRONTEND_URL")

SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_spotify_token():
    auth = base64.b64encode(
        f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}".encode()
    ).decode()

    res = requests.post(
        "https://accounts.spotify.com/api/token",
        headers={
            "Authorization": f"Basic {auth}",
            "Content-Type": "application/x-www-form-urlencoded"
        },
        data={
            "grant_type": "client_credentials"
        }
    )

    return res.json().get("access_token")

# =========================
# HEALTH CHECK
# =========================
@router.get("/")
def home():
    return {"name": "HMBL API", "status": "online"}

@router.get("/ping")
async def ping():
    return {"status": "ok"}


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

        # ================= TOKEN =================
        token_res = requests.post(
            "https://discord.com/api/oauth2/token",
            data={
                "client_id": DISCORD_CLIENT_ID,
                "client_secret": DISCORD_CLIENT_SECRET,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": DISCORD_REDIRECT_URI,
            },
            headers={
                "Content-Type": "application/x-www-form-urlencoded"
            }
        )

        token_json = token_res.json()

        access_token = token_json.get("access_token")

        if not access_token:
            return RedirectResponse(
                f"{FRONTEND_URL}/?error=oauth_failed"
            )

        # ================= USER =================
        user_res = requests.get(
            "https://discord.com/api/users/@me",
            headers={
                "Authorization": f"Bearer {access_token}"
            }
        )

        user = user_res.json()

        discord_id = user.get("id")
        username_raw = user.get("username", "user")
        avatar = user.get("avatar")

        if not discord_id:
            return RedirectResponse(
                f"{FRONTEND_URL}/?error=user_failed"
            )

        # ================= DISCORD PFP =================
        avatar_url = None

        if avatar:
            avatar_url = (
                f"https://cdn.discordapp.com/avatars/"
                f"{discord_id}/{avatar}.png?size=512"
            )

        # ================= EXISTING PLAYER =================
        existing = supabase.table("players") \
            .select("*") \
            .eq("discord_id", discord_id) \
            .execute()

        is_new_user = not existing.data

        # ================= CREATE PLAYER =================
        if is_new_user:

            hmbl_username = (
                f"{username_raw.lower()}_{discord_id[-4:]}"
            )

            supabase.table("players").insert({
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

        else:

            existing_player = existing.data[0]

            hmbl_username = existing_player["username"]

            # ALWAYS UPDATE PFP ON LOGIN
            supabase.table("players") \
                .update({
                    "pfp": avatar_url
                }) \
                .eq("discord_id", discord_id) \
                .execute()

        # ================= JWT =================
        token = jwt.encode(
            {
                "discord_id": discord_id,
                "username": hmbl_username,
                "pfp": avatar_url,
                "is_new": is_new_user,
                "exp": datetime.utcnow() + timedelta(days=30)
            },
            JWT_SECRET,
            algorithm="HS256"
        )

        return RedirectResponse(
            f"{FRONTEND_URL}/?token={token}&new={str(is_new_user).lower()}"
        )

    except Exception as e:
        print("DISCORD CALLBACK ERROR:", e)

        return RedirectResponse(
            f"{FRONTEND_URL}/?error=server_error"
        )


# =========================
# AUTH ME
# =========================
@router.get("/auth/me")
def get_me(authorization: str = Header(None)):

    if not authorization:
        return {
            "status": "error",
            "message": "missing token"
        }

    try:

        token = authorization.replace("Bearer ", "")

        data = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=["HS256"]
        )

        player = supabase.table("players") \
            .select("*") \
            .eq("discord_id", data["discord_id"]) \
            .single() \
            .execute()

        return {
            "status": "success",

            # IMPORTANT:
            # frontend should use THIS
            "user": player.data
        }

    except Exception as e:
        print("AUTH ME ERROR:", e)

        return {
            "status": "error",
            "message": "invalid token"
        }


# =========================
# NEED SETUP CHECK
# =========================
@router.get("/auth/needs-setup")
def needs_setup(authorization: str = Header(None)):

    if not authorization:
        return {"status": "error"}

    try:

        token = authorization.replace("Bearer ", "")

        data = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=["HS256"]
        )

        player = supabase.table("players") \
            .select("position") \
            .eq("discord_id", data["discord_id"]) \
            .single() \
            .execute()

        return {
            "status": "success",
            "needs_setup": (
                player.data and
                player.data.get("position") is None
            )
        }

    except:
        return {"status": "error"}


# =========================
# UPDATE PROFILE
# =========================
@router.post("/players/update-profile")
def update_profile(payload: dict, authorization: str = Header(None)):

    if not authorization:
        return {"status": "error", "message": "missing token"}

    try:

        token = authorization.replace("Bearer ", "")
        data = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])

        discord_id = data["discord_id"]

        username = payload.get("username")
        position = payload.get("position")
        country = payload.get("country")
        music = payload.get("music")

        twitter = payload.get("twitter")
        instagram = payload.get("instagram")
        tiktok = payload.get("tiktok")

        if not username:
            return {"status": "error", "message": "missing username"}

        supabase.table("players").update({
            "username": username,
            "position": position,
            "country": country,
            "twitter": twitter,
            "instagram": instagram,
            "tiktok": tiktok,
            "music": music
        }).eq("discord_id", discord_id).execute()

        return {"status": "success"}

    except Exception as e:
        print("UPDATE PROFILE ERROR:", repr(e))
        return {
            "status": "error",
            "message": str(e)
        }


# =========================
# INCREMENT VIEW
# =========================
@router.post("/players/increment-view")
def increment_view(payload: dict):

    username = payload.get("username")

    if not username:
        return {"status": "error"}

    player = supabase.table("players") \
        .select("profile_views") \
        .eq("username", username) \
        .execute()

    if not player.data:
        return {"status": "error"}

    current = player.data[0].get(
        "profile_views",
        0
    )

    supabase.table("players") \
        .update({
            "profile_views": current + 1
        }) \
        .eq("username", username) \
        .execute()

    return {"status": "success"}


# =========================
# GET PLAYERS
# =========================
@router.get("/players")
def get_players():

    res = supabase.table("players") \
        .select("*") \
        .execute()

    return {
        "status": "success",
        "data": {
            str(p["id"]): p
            for p in (res.data or [])
        }
    }


# =========================
# GET TEAMS
# =========================
@router.get("/teams")
def get_teams():

    res = supabase.table("teams") \
        .select("*") \
        .execute()

    return {
        "status": "success",
        "data": {
            str(t["id"]): t
            for t in (res.data or [])
        }
    }


# =========================
# GET DIVISIONS
# =========================
@router.get("/divisions")
def get_divisions():

    res = supabase.table("divisions") \
        .select("*") \
        .execute()

    return {
        "status": "success",
        "data": {
            d["name"]: d
            for d in (res.data or [])
        }
    }


# =========================
# GET MATCHES
# =========================
@router.get("/matches")
def get_matches():

    res = supabase.table("matches") \
        .select("*") \
        .execute()

    return {
        "status": "success",
        "data": {
            str(m["id"]): m
            for m in (res.data or [])
        }
    }


# =========================
# SPOTIFY TRACK
# =========================
@router.post("/spotify-track")
def spotify_track(payload: dict):

    url = payload.get("url")

    if not url or "/track/" not in url:
        return {"status": "error", "message": "invalid url"}

    try:
        track_id = url.split("/track/")[1].split("?")[0]

        token = get_spotify_token()

        if not token:
            return {"status": "error", "message": "spotify auth failed"}

        res = requests.get(
            f"https://api.spotify.com/v1/tracks/{track_id}",
            headers={
                "Authorization": f"Bearer {token}"
            }
        )

        if res.status_code != 200:
            return {"status": "error", "message": "track not found"}

        track = res.json()

        return {
            "status": "success",

            "track": {
                "name": track.get("name"),
                "id": track.get("id"),

                "artist": ", ".join(
                    a["name"] for a in track.get("artists", [])
                ),

                "album": track.get("album", {}).get("name"),

                "cover": track.get("album", {})
                    .get("images", [{}])[0]
                    .get("url"),

                "preview": track.get("preview_url"),

                "duration_ms": track.get("duration_ms"),

                "spotify_url": track.get("external_urls", {}).get("spotify")
            }
        }

    except Exception as e:
        print("SPOTIFY ERROR:", repr(e))
        return {"status": "error", "message": "failed to fetch track"}



@router.post("/auth/check-role")
def check_role(payload: dict, authorization: str = Header(None)):

    if not authorization:
        return {"status": "error", "message": "missing token"}

    try:
        token = authorization.replace("Bearer ", "")
        data = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])

        discord_id = data["discord_id"]
        required_role = payload.get("role")

        if not required_role:
            return {"status": "error", "message": "missing role"}

        # Discord API call (no bot needed yet)
        headers = {
            "Authorization": f"Bot {os.getenv('DISCORD_BOT_TOKEN')}"
        }

        res = requests.get(
            f"https://discord.com/api/guilds/{os.getenv('DISCORD_GUILD_ID')}/members/{discord_id}",
            headers=headers
        )

        if res.status_code != 200:
            return {"status": "error", "message": "member not found"}

        member = res.json()

        roles = member.get("roles", [])

        has_role = required_role in roles

        return {
            "status": "success",
            "allowed": has_role
        }

    except Exception as e:
        print("ROLE CHECK ERROR:", e)
        return {"status": "error"}
