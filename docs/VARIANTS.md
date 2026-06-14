# Variants & output modes

Two additions that ship alongside the core API, both meant for experimentation
and scripting. Neither changes any existing endpoint or its response shape.

## 1. Landing page A/B test (`?variant=b`)

The home page (`/`) can serve one of two hero designs so you can measure which
converts better:

| | Variant A (default) | Variant B |
|---|---|---|
| Headline | "Receipt Spending Analyzer" (product name) | "Stop losing money to paper receipts." (benefit-led) |
| Layout | single column, four feature cards | two-column split hero with a live terminal demo |
| CTA | two buttons (uploader + health) | one high-intent button ("Start scanning — it's free") |
| Palette | green / cyan | amber / indigo |
| Template | `templates/index.html` | `templates/index_b.html` |

Both share the same endpoint list and the same live `/v1/health` status probe.

### How the bucketing works

- `GET /?variant=b` → serves variant B and drops a `landing_variant=b` cookie
  (30-day TTL).
- `GET /?variant=a` → serves variant A and resets the cookie to `a`.
- `GET /` with no query → serves whatever the cookie says (defaults to `a`),
  so a visitor stays in the same bucket across reloads.

Only the `/` route changed in `run.py`; everything else is a new template.

```bash
curl -s "http://127.0.0.1:5000/?variant=b" | grep -o "Stop losing money"
```

## 2. Terminal dashboard (`cli.py`)

A premium, read-only TUI that talks to the running API over HTTP. Browse
workspaces, inspect transactions, watch budget bars fill up in colour and read
an in-terminal spend breakdown — all without leaving your shell.

```bash
python cli.py                 # launch the interactive dashboard
python cli.py health          # one-shot API health check
python cli.py workspaces      # list workspaces as a table
python cli.py show <id>       # full dashboard for one workspace
```

Config via env:

| Variable | Default | Purpose |
|---|---|---|
| `AIRECEIPT_URL` | `http://127.0.0.1:5000` | base URL of the running API |
| `AIRECEIPT_TOKEN` | `me` | bearer token / user id |
| `AIRECEIPT_CURRENCY` | `$` | currency symbol used in the display |

The interface uses [`rich`](https://github.com/Textualize/rich) when installed
and degrades to a clean, dependency-free plain-text mode when it is not — so it
always runs. Colour is auto-disabled when piped or when `NO_COLOR` is set.
