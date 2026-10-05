# Retro Games Support Bot
A customer-support chatbot for an online retro video game store, built on a REST API with JWT authentication. Customers ask in natural language about **their own** orders, shipments, returns and purchase history, and an LLM answers by calling a fixed set of scoped tools. It never sees, and cannot ask for, anyone else's data.

![Chat: shipping and purchase stats](docs/chat-shipping.png)

## Features

- **REST API** (Flask + SQLAlchemy) with registration, login and JWT-protected endpoints.
- **Chatbot** powered by Gemini function calling, with 9 tools over the same service layer the API uses.
- **Per-customer data isolation**: every query is filtered by the authenticated user, enforced and tested at several layers.
- **Safe write actions**: the bot can *prepare* a return, but only the customer can *confirm* it, through a separate endpoint the model cannot call.
- **Purchase analytics** answered with SQL, not by the model: favorite genres, best month, spending summary, top products.
- **Web chat UI**: a single static HTML page served by Flask (no build step).
- **30+ automated tests**, none of them requiring network access or an API key.

| Return confirmation | Refusing other customers' data |
|---|---|
| ![Return confirmation](docs/chat-return.png) | ![Security](docs/chat-security.png) |

## How it works

```mermaid
sequenceDiagram
    participant B as Browser
    participant A as Flask API
    participant L as Gemini
    participant D as SQLite

    B->>A: POST /ask {message} + JWT
    A->>A: user_id = subject of the verified JWT
    A->>L: message + tool declarations (no user_id parameter)
    L-->>A: call get_order_details(order_id=19)
    A->>D: SELECT ... WHERE id = 19 AND user_id = <from token>
    D-->>A: rows
    A->>L: tool result
    L-->>A: final answer
    A-->>B: reply (+ pending_action if a return is waiting for confirmation)
```

The model does two things: turn a question into a tool call, and turn the result into a sentence. It does not write SQL, does not do the math, and has no way to reach data that no tool exposes.

### Chatbot tools

| Tool | What it does |
|---|---|
| `search_products` | Catalog search by name, genre and console (public data) |
| `get_my_orders` | The customer's orders, newest first, optional status filter |
| `get_order_details` | Items, prices, address and returns of one order |
| `track_shipment` | Carrier, tracking code, status and ETA of one order |
| `purchase_stats` | Games bought grouped by month, genre or console |
| `spending_summary` | Total spent, number of orders, average order value |
| `top_products` | Most purchased products by units |
| `get_my_returns` | The customer's return requests and their status |
| `request_return` | Validates a return and stores it as *pending*; **writes nothing** |

## Security design

The point of the project is that a chatbot connected to customer data must not be able to leak it, even if the model is tricked.

- **`user_id` comes only from the verified JWT.** Never from the request body, the query string or the model. A `?user_id=2` is ignored (tested).
- **No tool has a `user_id` parameter.** The tools are closures built per request that capture the id from the token (tested by inspecting every tool signature).
- **Every service query filters by user.** A foreign order and a non-existent order return the *same* 404, so ids cannot be enumerated (tested).
- **Authentication errors reveal nothing.** Unknown email and wrong password give identical 401 responses. `/auth/register` never reads a `role` from the payload.
- **Writes need out-of-band confirmation.** `request_return` only stores a pending proposal (expires after 5 minutes, discarded by any new message). The return is created by `POST /ask/confirm`, which the model cannot trigger.
- **User input never reaches SQL.** `group_by` is validated against a whitelist; everything else is bound parameters through SQLAlchemy.
- **Limited exposure.** Serializers return a fixed list of fields (`password_hash` is never serialized), passwords are hashed with Werkzeug, messages are capped at 500 characters and history at 10 turns.
- **Front-end hygiene.** The JWT lives in JavaScript memory (not `localStorage`) and model output is HTML-escaped before rendering, so it cannot inject markup.

## Tech stack

Python 3.13 · Flask · Flask-SQLAlchemy · Flask-JWT-Extended · SQLite · Google Gemini API (`google-genai`) · pytest · vanilla HTML/JS

## Getting started

Requirements: Python 3.11+ and a free [Google AI Studio](https://aistudio.google.com) API key.

```bash
git clone https://github.com/raftontheshore/support-bot-videogame-store.git
cd support-bot-videogame-store

python -m venv .venv
# Windows (PowerShell):  .\.venv\Scripts\Activate.ps1
# macOS / Linux:         source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env        # Windows: Copy-Item .env.example .env
```

Edit `.env`:

| Variable | Description |
|---|---|
| `JWT_SECRET_KEY` | Long random string. Generate one with `python -c "import secrets; print(secrets.token_hex(32))"` |
| `SECRET_KEY` | Flask secret key |
| `GEMINI_API_KEY` | Your Google AI Studio key |
| `GEMINI_MODEL` | A Gemini Flash / Flash-Lite model that supports function calling. `python -m scripts.gemini_check` lists the ones your key can use |
| `DATABASE_URL` | Defaults to `sqlite:///app.db` |

Create the demo data and start the server:

```bash
python -m scripts.seed
python -m flask --app app run --debug --port 8000
```

Open <http://127.0.0.1:8000/> and sign in with a demo account. All passwords are `test1234`.

| Customer | Email | Buys mostly |
|---|---|---|
| Ana Pérez | `ana@example.com` | RPG, Adventure |
| Bruno Gómez | `bruno@example.com` | Racing, Sports |
| Carla Díaz | `carla@example.com` | Platformer, Puzzle |

The seed also creates an `admin@example.com` user (the `role` column is already in the model, but no admin features exist yet). Data is synthetic and spread over the last 12 months, and every customer has one recent shipped, pending and delivered order to play with.

> **Note on the free tier:** each chat message can trigger several model calls (one per tool step plus the final answer), and free-tier limits are low. If you get a 429, wait a minute or pick a model with a higher limit.

### Running the tests

```bash
python -m pytest -q
```

Tests use an in-memory database and a fixed JWT key, and never call Gemini.

### Try the API without the UI

```bash
python -m scripts.smoke       # logs in as Ana and Bruno and exercises the endpoints (server must be running)
python -m scripts.chat_demo   # interactive chat in the terminal
```

## API reference

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/` | – | Web chat UI |
| GET | `/health` | – | Health check |
| POST | `/auth/register` | – | Create a customer account |
| POST | `/auth/login` | – | Returns a JWT access token (1 hour) |
| GET | `/auth/me` | JWT | Current user |
| GET | `/products?q=&genre=&console=&page=&per_page=` | – | Catalog search |
| GET | `/orders?status=&page=&per_page=` | JWT | Own orders |
| GET | `/orders/<id>` | JWT | Own order details |
| GET | `/orders/<id>/shipment` | JWT | Shipment of an own order |
| GET | `/returns` | JWT | Own return requests |
| POST | `/returns` | JWT | Request a return `{order_id, reason}` (delivered orders only) |
| GET | `/stats/purchases?group_by=month\|genre\|console&year=` | JWT | Purchase stats |
| POST | `/ask` | JWT | Chatbot `{message, history?}` → `{reply, pending_action}` |
| POST | `/ask/confirm` | JWT | Confirms the pending return proposed by the bot |

Example:

```bash
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"ana@example.com","password":"test1234"}' | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

curl -s http://127.0.0.1:8000/stats/purchases?group_by=genre -H "Authorization: Bearer $TOKEN"
```

## Data model

Adapted from the schema I designed in a university databases course (UNNE), translated to English and extended with shipments and returns.

```mermaid
erDiagram
    CATEGORY ||--o{ PRODUCT : classifies
    PRODUCT ||--o{ ORDER_ITEM : "is bought in"
    ORDER ||--|{ ORDER_ITEM : contains
    USER ||--o{ ORDER : places
    ADDRESS ||--o{ ORDER : "ships to"
    ADDRESS |o--o| USER : "lives at"
    ORDER ||--o| SHIPMENT : has
    ORDER ||--o{ RETURN_REQUEST : "may have"
```

`Category` holds the game genres. `OrderItem.unit_price` stores the price paid at purchase time, so history survives later price changes.

## Project structure

```
app/
  __init__.py      app factory, JWT setup, error handlers
  models.py        SQLAlchemy models
  services.py      all data access; every per-user function requires user_id
  auth.py          register / login / me
  routes.py        REST endpoints and the chat page
  chat.py          Gemini tool calling, pending-action confirmation
  static/index.html  web chat UI
scripts/           seed, smoke test, terminal chat, Gemini diagnostics
tests/             auth, isolation, returns, chat tools, front-end
```

## Known limitations and roadmap
- The pending-return store is in memory (lost on restart); production would use a DB table or Redis.
- Conversation history is sent by the client. It only affects that user's own conversation, but a server-side store would be cleaner.
- No per-user rate limiting on `/ask`; Flask-Limiter would be the next addition, since every message costs model calls.
- Prices are floats for simplicity; production would use `Numeric` or integer cents.
- Planned: admin role with RBAC and audit log, Postgres + Alembic migrations, Docker, and a WhatsApp/Telegram channel.

## Author
[@raftontheshore](https://github.com/raftontheshore)
