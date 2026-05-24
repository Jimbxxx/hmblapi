import json
import os
import threading

DATA_PATH = "data"

class Database:
    def __init__(self):
        self.lock = threading.Lock()

        # shared cache (your choice)
        self.cache = {
            "teams": {},
            "divisions": {},
            "players": {},
            "matches": {},
            "transfers": {},
            "settings": {}
        }

        self.files = {
            "teams": "teams.json",
            "divisions": "divisions.json",
            "players": "players.json",
            "matches": "matches.json",
            "transfers": "transfers.json",
            "settings": "settings.json"
        }

        self._ensure_files()
        self.load_all()

    # ------------------------
    # FILE HANDLING
    # ------------------------

    def _ensure_files(self):
        os.makedirs(DATA_PATH, exist_ok=True)

        for name, file in self.files.items():
            path = os.path.join(DATA_PATH, file)

            if not os.path.exists(path):
                with open(path, "w") as f:
                    json.dump({}, f)

    def load_all(self):
        for name, file in self.files.items():
            path = os.path.join(DATA_PATH, file)

            try:
                with open(path, "r") as f:
                    self.cache[name] = json.load(f)
            except:
                self.cache[name] = {}

    def save(self, name: str):
        """Instant save to file"""
        with self.lock:
            path = os.path.join(DATA_PATH, self.files[name])

            with open(path, "w") as f:
                json.dump(self.cache[name], f, indent=4)

    # ------------------------
    # TEAM FUNCTIONS
    # ------------------------

    def get_team(self, team_id):
        return self.cache["teams"].get(team_id)

    def set_team(self, team_id, data):
        self.cache["teams"][team_id] = data
        self.save("teams")

    def delete_team(self, team_id):
        if team_id in self.cache["teams"]:
            del self.cache["teams"][team_id]
            self.save("teams")

    # ------------------------
    # DIVISION FUNCTIONS
    # ------------------------

    def get_division(self, div):
        return self.cache["divisions"].get(div)

    def set_division(self, div, data):
        self.cache["divisions"][div] = data
        self.save("divisions")

    def delete_division(self, div):
        if div in self.cache["divisions"]:
            del self.cache["divisions"][div]
            self.save("divisions")

    # ------------------------
    # ID GENERATION
    # ------------------------

    def generate_team_id(self):
        existing = self.cache["teams"].keys()

        i = 1
        while True:
            tid = f"TEAM_{i:03}"
            if tid not in existing:
                return tid
            i += 1


db = Database()