import requests

BASE = "http://127.0.0.1:8000"
PASSWORD = "test1234"


def login(email):
    r = requests.post(f"{BASE}/auth/login", json={"email": email, "password": PASSWORD})
    r.raise_for_status()
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def show(title, response):
    print(f"\n== {title} -> {response.status_code}")
    print(response.text[:500])


ana = login("ana@example.com")
bruno = login("bruno@example.com")

show("GET /products?genre=RPG&per_page=2 (public)",
     requests.get(f"{BASE}/products", params={"genre": "RPG", "per_page": 2}))

delivered = requests.get(f"{BASE}/orders", params={"status": "delivered", "per_page": 1}, headers=ana)
show("GET /orders?status=delivered&per_page=1 (Ana)", delivered)
ana_order = delivered.json()["items"][0]["id"]

show(f"GET /orders/{ana_order} (Ana, her own order)",
     requests.get(f"{BASE}/orders/{ana_order}", headers=ana))
show(f"GET /orders/{ana_order}/shipment (Ana)",
     requests.get(f"{BASE}/orders/{ana_order}/shipment", headers=ana))

bruno_order = requests.get(f"{BASE}/orders", headers=bruno).json()["items"][0]["id"]
show(f"Ana asks for Bruno's order #{bruno_order}",
     requests.get(f"{BASE}/orders/{bruno_order}", headers=ana))

show("GET /stats/purchases?group_by=genre (Ana)",
     requests.get(f"{BASE}/stats/purchases", params={"group_by": "genre"}, headers=ana))
show("GET /stats/purchases?group_by=month (Bruno)",
     requests.get(f"{BASE}/stats/purchases", params={"group_by": "month"}, headers=bruno))

show("GET /orders without token", requests.get(f"{BASE}/orders"))