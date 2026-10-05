import sys

import requests

BASE = "http://127.0.0.1:8000"
PASSWORD = "test1234"

email = sys.argv[1] if len(sys.argv) > 1 else "ana@example.com"
r = requests.post(f"{BASE}/auth/login", json={"email": email, "password": PASSWORD})
r.raise_for_status()
headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

print(f"Logged in as {email}. Type 'exit' to quit.\n")
history = []
while True:
    message = input("you> ").strip()
    if message.lower() in {"exit", "quit"}:
        break
    if not message:
        continue

    r = requests.post(f"{BASE}/ask", json={"message": message, "history": history}, headers=headers)
    if r.status_code != 200:
        print(f"[error {r.status_code}] {r.json().get('error')}\n")
        continue

    data = r.json()
    print(f"bot> {data['reply']}\n")
    history += [{"role": "user", "text": message}, {"role": "model", "text": data["reply"]}]

    pending = data.get("pending_action")
    if pending:
        answer = input(f"Confirm return for order #{pending['order_id']}? (y/n) ").strip().lower()
        if answer == "y":
            c = requests.post(f"{BASE}/ask/confirm", headers=headers)
            print(f"[{c.status_code}] {c.json()}\n")
        else:
            print("Not confirmed.\n")