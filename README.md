# 🧾 Receipt Spending Analyzer

> Snap a receipt, let an LLM read every crumpled line item, and watch a shoebox of paper
> turn into clean categories, budgets and honest-to-goodness saving advice.

A tidy little **Flask** API that does the boring part of budgeting for you. Upload a photo of a
receipt, a vision model extracts each item, price, vendor and date, matches everything to your own
spending categories, and then hands you reports, charts, budget alerts and an AI advisor that
actually knows what you bought. No database, no heavyweight setup — just CSV and JSON files on disk.

<p align="center">
  <img src="docs/media/landing-desktop.png" alt="Receipt Spending Analyzer landing page" width="100%" />
</p>

<p align="center">
  <img src="docs/media/upload-desktop.png" alt="Receipt upload page" width="60%" />
  &nbsp;
  <img src="docs/media/landing-mobile.png" alt="Mobile layout" width="30%" />
</p>

---

## ✨ What it does

- **🧾 Scan & parse** — a vision LLM pulls items, prices, vendor and purchase date straight from a photo.
- **🏷️ Auto-categorise** — every line item is matched to your workspace's categories, and brand-new
  categories are created on the fly when nothing fits.
- **📁 Workspaces** — keep separate budgets (personal, business, "that trip to Karachi") side by side.
- **💸 Transactions & budgets** — query spending and set per-category limits with utilisation tracking.
- **📊 Reports & charts** — daily / weekly / monthly totals, top items, top categories, plus pie / bar /
  line chart data and one-click CSV export.
- **🧠 AI insights & advice** — personalised saving suggestions, budget-overage detection and a
  conversational chatbot that answers questions about *your* spending.
- **🩺 Health check** — a plain liveness endpoint for your uptime monitor.

Everything persists to lightweight files under `storage/` — perfect for a demo, a hackathon, or a
self-hosted personal tool.

---

## 🏗️ How it's built

| Layer            | Choice                                             |
| ---------------- | -------------------------------------------------- |
| Web framework    | Flask 3 (blueprint-per-domain)                     |
| AI               | OpenAI (vision for parsing, chat for advice)       |
| Data crunching   | pandas over CSV / JSON files — no DB to babysit    |
| Charts           | matplotlib (headless `Agg` backend)                |
| Config           | `python-dotenv` (`.env`)                           |

The code is organised so each concern lives in its own place:

```
app/
├── routes/        # thin HTTP handlers (one blueprint per area)
├── services/      # the actual business logic
│   └── aggregators/   # report math: items, categories, summaries
└── utils/         # LLM calls, image saving, CSV queries
templates/         # landing page + receipt uploader
run.py             # app factory + entry point
```

---

## 🚀 Get it running (5 minutes, promise)

### Prerequisites

- **Python 3.9+** (developed on 3.11) — check with `python3 --version`
- **pip** and the ability to make a virtual environment
- An **OpenAI API key** — *only* needed for the AI features (parsing, advice, chat). The workspace,
  category, transaction and report endpoints work perfectly fine without one.

### 1. Clone & enter

```bash
git clone https://github.com/waleedsworld/Ai-Reciept.git
cd Ai-Reciept
```

### 2. Create and activate a virtual environment

```bash
python3 -m venv .venv

# macOS / Linux
source .venv/bin/activate

# Windows (PowerShell)
.venv\Scripts\Activate.ps1
```

### 3. Install the dependencies

```bash
pip install -r requirements.txt
```

### 4. Add your API key

```bash
cp .env.example .env
# then open .env and paste your key:
# OPENAI_API_KEY=sk-...
```

### 5. Run it

```bash
python run.py
```

Open **http://127.0.0.1:5000** and you'll get the friendly landing page with a live API map. That's it! 🎉

> Want a different port? `PORT=8080 python run.py`.

### Kick the tyres without a key

There's a zero-dependency-on-OpenAI smoke test that creates a workspace, seeds categories and reads
them back:

```bash
python test.py
```

---

## 📡 API reference

Base URL is `/v1`. Auth is a bearer token (`Authorization: Bearer <token>`) — in this reference
build the token doubles as the user id, so pick any string and stay consistent.

### Workspaces
| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/v1/instances` | Create a workspace |
| `GET` | `/v1/instances` | List your workspaces |
| `GET` | `/v1/instances/<id>` | Workspace details + total spend |
| `PUT` | `/v1/instances/<id>` | Rename / archive |
| `DELETE` | `/v1/instances/<id>` | Delete a workspace |

### Categories
| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/v1/instances/<id>/initialize` | Bulk-seed categories (comma separated) |
| `POST` | `/v1/instances/<id>/categories` | Add one category |
| `PUT` / `POST` | `/v1/categories/<cat_id>` | Rename a category |
| `DELETE` | `/v1/categories/<cat_id>` | Delete a category |

### Receipts
| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/v1/reciepts` | Upload an image → parsed + categorised items |
| `GET` | `/v1/reciepts/<id>` | Fetch a parsed receipt |
| `PATCH` | `/v1/reciepts/<id>` | Correct line items and re-sync the CSV |

### Transactions & budgets
| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/v1/instances/<id>/transactions` | List transactions |
| `POST` | `/v1/instances/<id>/budgets` | Create / update a category budget |
| `GET` | `/v1/instances/<id>/budgets` | Budget utilisation (spent vs limit) |

### Reports & insights
| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/v1/instances/<id>/reports` | Numeric report (`?period=weekly\|monthly\|custom`) |
| `GET` | `/v1/instances/<id>/graphs` | Chart-ready data |
| `GET` | `/v1/instances/<id>/export` | Stream the raw CSV |
| `POST` | `/v1/instances/<id>/advice` | Generate saving advice |
| `POST` | `/v1/instances/<id>/chat` | Chat about your spending |
| `GET` | `/v1/health` | Liveness check |

### Try it with curl

```bash
# 1. Create a workspace
curl -X POST http://127.0.0.1:5000/v1/instances \
  -H "Authorization: Bearer me" \
  -H "Content-Type: application/json" \
  -d '{"name":"My Budget"}'

# 2. Seed some categories (use the instance_id from step 1)
curl -X POST http://127.0.0.1:5000/v1/instances/<id>/initialize \
  -H "Authorization: Bearer me" \
  -H "Content-Type: application/json" \
  -d '{"categories":"Groceries, Transport, Coffee"}'

# 3. Upload a receipt (needs OPENAI_API_KEY)
curl -X POST http://127.0.0.1:5000/v1/reciepts \
  -H "Authorization: Bearer me" \
  -F "reciept=@receipt.jpg" \
  -F "instance_id=<id>"
```

Prefer clicking? Head to **/upload** for a drag-and-drop uploader that shows the parsed JSON inline.

---

## 🌐 Live demo

Live demo — deploying soon.

---

## 🗺️ Roadmap ideas

- Swap CSV storage for SQLite when a workspace gets big.
- Multi-currency support (totals currently assume PKR).
- Recurring-charge detection ("you've paid Netflix 3 months running").

---

## 📜 License

MIT — use it, fork it, expense it. Attribution appreciated.
