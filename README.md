# SmartRuleAI — Web Edition

A rule-based cybersecurity chatbot that **shows its work**. Instead of a
black-box model, it reasons over an explicit, editable **Knowledge Base**
(facts) and **Rule Base** (`IF … THEN …` productions) using forward
chaining, and renders every step of that chain in a live "Reasoning
trace" panel.

This is a rebuild of the original CustomTkinter desktop app as a Flask
web app so it can be deployed to Railway (or any host that runs a WSGI
app) and used from a browser or phone.

## What's new vs. the desktop version

- **Web UI** — a console-styled interface (Flask + vanilla JS, no build
  step) with a chat panel, a live reasoning-trace side panel, and
  dedicated tools, all responsive down to mobile.
- **Mood-aware greeting** — the opening message adapts to the time of
  day server-side, and the chatbot detects the tone of each message
  (stressed, frustrated, tired, happy, curious) via an explicit pattern
  table (`mood.py`) and softens its reply accordingly.
- **Security Checklist tool** — an 8-question quiz that feeds every
  answer into the *same* forward-chaining engine used by chat, then
  reports a live score, a rating, and targeted recommendations.
- **Expanded Knowledge/Rule Base** — grew from 17 facts / 11 rules to
  roughly 60 facts and 45 rules covering passwords, authentication,
  network security, malware, data & privacy, social engineering, mobile
  and physical security, and incident planning — several rule chains
  now converge on the same conclusion from different starting points.
- **More tools** — Knowledge Base and Rule Base browsers with
  add/delete, quick-question chips, a random-tip button, searchable
  conversation history with export, and a stats readout.
- **JSON REST API** under `/api/*` so the reasoning engine can be reused
  from any client, not just the bundled UI.

## Project structure

```
SmartRuleAI/
├── app.py              Flask app + REST API routes
├── database.py          SQLite layer (facts, rules, conversations)
├── seed_data.py          Starter facts + rules
├── knowledge_base.py     Fact model / concept matching
├── rules.py               Rule model
├── reasoning_engine.py    Forward-chaining inference
├── chatbot.py             Conversational orchestration, mood, checklist
├── mood.py                 Time greeting + declarative mood detection
├── templates/index.html    Single-page UI shell
├── static/style.css        Console-styled design system
├── static/script.js        Frontend logic (fetch-based, no build step)
├── requirements.txt
├── Procfile                 gunicorn start command
└── railway.json             Railway build/deploy config
```

## Run locally

```bash
pip install -r requirements.txt
python app.py
```

Then open http://localhost:5000

## Deploy to Railway

1. Push this folder to a GitHub repo (or use `railway up` from the CLI
   directly in this folder).
2. In Railway: **New Project → Deploy from GitHub repo**, pick the repo.
3. Railway auto-detects Python via Nixpacks and installs
   `requirements.txt`. The included `Procfile` / `railway.json` tell it
   to start with:
   ```
   gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 60
   ```
4. No environment variables are required to boot. Optional:
   - `SMARTRULE_DB` — override the SQLite filename (default
     `smartrule_ai.db`).
5. Once deployed, open the generated `*.up.railway.app` URL.

**Note on storage:** Railway's filesystem is ephemeral between deploys
unless you attach a persistent volume. SQLite works fine for a demo/
portfolio deployment, but facts, rules and chat history added at
runtime will reset on redeploy. For durable storage, attach a Railway
volume and point `SMARTRULE_DB` at a path inside it, or swap
`database.py` for a hosted Postgres connection.

## API quick reference

| Method | Path              | Purpose                                   |
|--------|-------------------|--------------------------------------------|
| GET    | `/api/greeting`   | Time-based greeting, stats, quick chips    |
| POST   | `/api/chat`       | `{message}` → response + mood + trace      |
| GET    | `/api/suggestions`| Random quick-question chips                |
| GET    | `/api/tip`        | Random fact from the knowledge base        |
| GET    | `/api/history`    | Conversation history (`?q=` to search)     |
| DELETE | `/api/history`    | Clear conversation history                 |
| GET/POST | `/api/facts`    | List / add facts                           |
| PUT/DELETE | `/api/facts/<id>` | Update / delete a fact                 |
| GET/POST | `/api/rules`    | List / add rules                           |
| DELETE | `/api/rules/<id>` | Delete a rule                              |
| GET    | `/api/stats`      | Fact/rule/conversation counts              |
| POST   | `/api/checklist`  | `{answers}` → score + recommendations      |

## Why forward chaining is a good fit here

Every derived fact is traceable to the exact rule and prior fact that
produced it, which is why the app can show a full explanation for any
answer instead of asking you to trust it.
