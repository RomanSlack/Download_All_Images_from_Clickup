import os
import requests
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("CLICKUP_TOKEN")
HEADERS = {"Authorization": TOKEN}
URL = "https://api.clickup.com/api/v2/team"

def main():
    resp = requests.get(URL, headers=HEADERS)
    resp.raise_for_status()
    teams = resp.json().get("teams", [])
    if not teams:
        print("No teams found.")
        return
    print("Workspace (team) IDs:")
    for t in teams:
        print(f"- {t['name']}: {t['id']}")

if __name__ == "__main__":
    main()
