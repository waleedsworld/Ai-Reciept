#!/usr/bin/env python3
"""Receipt Spending Analyzer — a premium terminal dashboard.

A rich, interactive TUI for the Flask API. Browse workspaces, inspect
transactions, watch budget utilisation fill up in colour, and read a spend
breakdown as an in-terminal bar chart — all without leaving your shell.

    python cli.py                 # launch the interactive dashboard
    python cli.py health          # one-shot API health check
    python cli.py workspaces      # list workspaces as a table
    python cli.py show <id>       # full dashboard for one workspace

Config via env:
    AIRECEIPT_URL    base URL of the running API   (default http://127.0.0.1:5000)
    AIRECEIPT_TOKEN  bearer token / user id        (default "me")

The interface uses `rich` when it is installed and degrades to a clean,
dependency-free plain-text mode when it is not — so it always runs.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

BASE_URL = os.environ.get("AIRECEIPT_URL", "http://127.0.0.1:5000").rstrip("/")
TOKEN = os.environ.get("AIRECEIPT_TOKEN", "me")

# Currency symbol — the app assumes a single currency; tweak freely.
CUR = os.environ.get("AIRECEIPT_CURRENCY", "$")

# --- Optional pretty layer ---------------------------------------------------
try:
    from rich.align import Align
    from rich.box import HEAVY, ROUNDED, SIMPLE_HEAVY
    from rich.console import Console, Group
    from rich.panel import Panel
    from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
    from rich.prompt import Prompt
    from rich.table import Table
    from rich.text import Text

    RICH = True
    console = Console()
except Exception:  # pragma: no cover - fallback path
    RICH = False
    console = None


# --- Tiny HTTP client (stdlib only) -----------------------------------------
def _request(method: str, path: str, body: dict | None = None, auth: bool = True):
    url = f"{BASE_URL}{path}"
    data = None
    headers = {"Content-Type": "application/json"}
    if auth:
        headers["Authorization"] = f"Bearer {TOKEN}"
    if body is not None:
        data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode()
            return resp.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {"error": raw or e.reason}
    except urllib.error.URLError as e:
        return 0, {"error": f"cannot reach {BASE_URL} ({e.reason})"}
    except Exception as e:  # pragma: no cover
        return 0, {"error": str(e)}


def _with_status(message: str, fn):
    """Run fn() while showing a spinner (rich) or a simple note (plain)."""
    if RICH:
        with console.status(f"[cyan]{message}[/]", spinner="dots"):
            return fn()
    print(f"... {message}")
    return fn()


# --- Palette / helpers -------------------------------------------------------
ACCENT = "#4ade80"
ACCENT2 = "#38bdf8"
MUTED = "#8b98a5"


def money(v) -> str:
    try:
        return f"{CUR}{float(v):,.2f}"
    except (TypeError, ValueError):
        return f"{CUR}0.00"


def util_style(pct: float) -> str:
    if pct >= 1.0:
        return "red"
    if pct >= 0.8:
        return "yellow"
    return "green"


# --- Rich renderers ----------------------------------------------------------
def banner():
    if not RICH:
        print("=" * 60)
        print("  RECEIPT SPENDING ANALYZER  ·  terminal dashboard")
        print(f"  {BASE_URL}   ·   token: {TOKEN}")
        print("=" * 60)
        return
    title = Text()
    title.append("🧾  Receipt Spending Analyzer\n", style=f"bold {ACCENT}")
    title.append("Turn a shoebox of paper into clean numbers", style=f"italic {MUTED}")
    meta = Text()
    meta.append("API ", style=MUTED)
    meta.append(BASE_URL, style=ACCENT2)
    meta.append("   token ", style=MUTED)
    meta.append(TOKEN, style="white")
    console.print(
        Panel(
            Group(Align.center(title), Text(""), Align.center(meta)),
            box=HEAVY,
            border_style=ACCENT,
            padding=(1, 4),
        )
    )


def check_health(quiet: bool = False) -> bool:
    status, data = _with_status("pinging the API", lambda: _request("GET", "/v1/health", auth=False))
    ok = status == 200 and data.get("status") == "ok"
    if quiet:
        return ok
    if not RICH:
        print(f"Health: {'ONLINE' if ok else 'OFFLINE'}  ({data})")
        return ok
    dot = "●"
    if ok:
        body = Text.assemble((f"{dot} ", "bold green"), ("API online", "bold green"),
                             ("   ·   ", MUTED), (data.get("time", ""), MUTED))
        console.print(Panel(body, box=ROUNDED, border_style="green", title="health"))
    else:
        msg = data.get("error", "no response")
        body = Text.assemble((f"{dot} ", "bold red"), ("API offline", "bold red"),
                             ("   ·   ", MUTED), (str(msg), MUTED))
        console.print(Panel(body, box=ROUNDED, border_style="red", title="health"))
    return ok


def fetch_workspaces() -> list[dict]:
    _, data = _with_status("loading workspaces", lambda: _request("GET", "/v1/instances"))
    if isinstance(data, dict):
        return data.get("instances", []) or []
    return []


def render_workspaces(workspaces: list[dict]):
    if not RICH:
        if not workspaces:
            print("(no workspaces yet — create one)")
            return
        for i, w in enumerate(workspaces, 1):
            print(f"  {i}. {w.get('name','?')}   [{w.get('id','')}]")
        return
    if not workspaces:
        console.print(
            Panel(
                Align.center(Text.assemble(
                    ("No workspaces yet\n", "bold"),
                    ("Create one to start tracking spending.", MUTED),
                )),
                box=ROUNDED, border_style=MUTED, padding=(2, 4), title="workspaces",
            )
        )
        return
    t = Table(box=SIMPLE_HEAVY, expand=True, border_style=MUTED, header_style=f"bold {ACCENT2}")
    t.add_column("#", justify="right", style=MUTED, width=3)
    t.add_column("Workspace", style="bold white")
    t.add_column("Instance id", style=ACCENT2, overflow="fold")
    for i, w in enumerate(workspaces, 1):
        t.add_row(str(i), w.get("name", "—"), w.get("id", ""))
    console.print(Panel(t, box=ROUNDED, border_style=ACCENT, title=f"workspaces · {len(workspaces)}"))


def render_transactions(rows: list[dict], total_rows: int):
    if not RICH:
        for r in rows:
            print(f"  {r.get('date','')}  {str(r.get('text',''))[:28]:<28}  {money(r.get('amount'))}  [{r.get('category','')}]")
        return
    if not rows:
        console.print(Panel(Align.center(Text("No transactions recorded yet.", style=MUTED)),
                            box=ROUNDED, border_style=MUTED, title="transactions"))
        return
    t = Table(box=SIMPLE_HEAVY, expand=True, border_style=MUTED, header_style=f"bold {ACCENT2}")
    t.add_column("Date", style=MUTED, no_wrap=True)
    t.add_column("Item", style="white")
    t.add_column("Category", style=ACCENT2)
    t.add_column("Amount", justify="right", style=f"bold {ACCENT}")
    for r in rows:
        t.add_row(str(r.get("date", "")), str(r.get("text", "")), str(r.get("category", "")), money(r.get("amount")))
    title = f"transactions · showing {len(rows)} of {total_rows}"
    console.print(Panel(t, box=ROUNDED, border_style=ACCENT, title=title))


def render_budgets(budgets: list[dict]):
    if not RICH:
        for b in budgets:
            limit = b.get("limit", 0) or 0
            spent = b.get("spent", 0) or 0
            pct = (spent / limit * 100) if limit else 0
            print(f"  {b.get('category',''):<14} {money(spent)}/{money(limit)}  ({pct:.0f}%)")
        return
    if not budgets:
        console.print(Panel(Align.center(Text("No budgets set. Set limits to track utilisation.", style=MUTED)),
                            box=ROUNDED, border_style=MUTED, title="budgets"))
        return
    rows = []
    for b in budgets:
        limit = float(b.get("limit", 0) or 0)
        spent = float(b.get("spent", 0) or 0)
        pct = (spent / limit) if limit else 0
        style = util_style(pct)
        bar_w = 24
        filled = min(bar_w, int(round(pct * bar_w)))
        bar = Text()
        bar.append("█" * filled, style=style)
        bar.append("░" * (bar_w - filled), style=MUTED)
        line = Text()
        line.append(f"{b.get('category','—'):<14}", style="bold white")
        line.append(bar)
        line.append(f"  {money(spent)} / {money(limit)}  ", style=MUTED)
        tag = f"{pct*100:>3.0f}%"
        line.append(tag, style=f"bold {style}")
        if pct >= 1.0:
            line.append("  OVER", style="bold red")
        rows.append(line)
    console.print(Panel(Group(*rows), box=ROUNDED, border_style=ACCENT, title="budget utilisation", padding=(1, 2)))


def render_breakdown(data: list[dict]):
    """In-terminal horizontal bar chart of spend per category."""
    if not data:
        return
    clean = []
    for d in data:
        label = str(d.get("label", "")).replace("Category ", "")
        val = float(d.get("value", 0) or 0)
        clean.append((label, val))
    clean.sort(key=lambda x: x[1], reverse=True)
    top = max((v for _, v in clean), default=0) or 1
    palette = [ACCENT, ACCENT2, "#fbbf24", "#c084fc", "#f87171", "#f472b6"]
    if not RICH:
        for label, val in clean:
            bar = "#" * int(val / top * 30)
            print(f"  {label:<12} {bar} {money(val)}")
        return
    rows = []
    width = 34
    for i, (label, val) in enumerate(clean):
        color = palette[i % len(palette)]
        filled = max(1, int(val / top * width))
        line = Text()
        line.append(f"{label:<12}", style="white")
        line.append("▐" + "█" * filled, style=color)
        line.append(f"  {money(val)}", style=f"bold {color}")
        rows.append(line)
    console.print(Panel(Group(*rows), box=ROUNDED, border_style=ACCENT2, title="spend by category", padding=(1, 2)))


def render_summary(detail: dict):
    if not RICH:
        print(f"\n  {detail.get('name','?')}   total spend: {money(detail.get('total_spend'))}")
        print(f"  categories: {len(detail.get('categories', []))}")
        return
    name = detail.get("name", "Workspace")
    total = money(detail.get("total_spend"))
    ncats = len(detail.get("categories", []))
    left = Text()
    left.append(f"{name}\n", style="bold white")
    left.append("total spend", style=MUTED)
    right = Text()
    right.append(f"{total}\n", style=f"bold {ACCENT}")
    right.append(f"{ncats} categories", style=ACCENT2)
    grid = Table.grid(expand=True)
    grid.add_column(justify="left")
    grid.add_column(justify="right")
    grid.add_row(left, right)
    console.print(Panel(grid, box=HEAVY, border_style=ACCENT, padding=(1, 3)))


# --- Composite views ---------------------------------------------------------
def show_workspace(instance_id: str):
    _, detail = _with_status("loading workspace", lambda: _request("GET", f"/v1/instances/{instance_id}"))
    if not isinstance(detail, dict) or detail.get("error"):
        err = detail.get("error", "not found") if isinstance(detail, dict) else "error"
        _error(f"Could not open workspace: {err}")
        return
    _, tx = _with_status("loading transactions", lambda: _request("GET", f"/v1/instances/{instance_id}/transactions"))
    _, budgets = _with_status("loading budgets", lambda: _request("GET", f"/v1/instances/{instance_id}/budgets"))
    _, graphs = _with_status("loading breakdown", lambda: _request("GET", f"/v1/instances/{instance_id}/graphs"))

    if RICH:
        console.print()
    render_summary(detail)
    tx_rows = tx.get("rows", []) if isinstance(tx, dict) else []
    render_transactions(tx_rows, tx.get("total_rows", len(tx_rows)) if isinstance(tx, dict) else 0)
    render_budgets(budgets.get("Details", []) if isinstance(budgets, dict) else [])
    render_breakdown(graphs.get("data", []) if isinstance(graphs, dict) else [])


def create_workspace_flow():
    name = _ask("Workspace name")
    if not name:
        return
    status, data = _with_status("creating workspace", lambda: _request("POST", "/v1/instances", {"name": name}))
    if status == 201:
        iid = data.get("instance_id", "")
        _ok(f"Created “{name}”  ·  {iid}")
        seed = _ask("Seed categories now? (comma separated, blank to skip)")
        if seed.strip():
            _with_status("seeding categories", lambda: _request("POST", f"/v1/instances/{iid}/initialize", {"categories": seed}))
            _ok("Categories seeded.")
    else:
        _error(data.get("error", "failed to create workspace"))


# --- Feedback primitives -----------------------------------------------------
def _ok(msg: str):
    if RICH:
        console.print(f"[bold green]✓[/] {msg}")
    else:
        print(f"[ok] {msg}")


def _error(msg: str):
    if RICH:
        console.print(Panel(Text(str(msg), style="red"), box=ROUNDED, border_style="red", title="error"))
    else:
        print(f"[error] {msg}")


def _ask(label: str) -> str:
    if RICH:
        return Prompt.ask(f"[{ACCENT2}]{label}[/]").strip()
    try:
        return input(f"{label}: ").strip()
    except EOFError:
        return ""


# --- Interactive menu --------------------------------------------------------
MENU = [
    ("1", "Dashboard (health + workspaces)"),
    ("2", "Open a workspace"),
    ("3", "Create a workspace"),
    ("4", "Health check"),
    ("q", "Quit"),
]


def menu():
    banner()
    while True:
        if RICH:
            t = Table.grid(padding=(0, 2))
            t.add_column(style=f"bold {ACCENT}", justify="right")
            t.add_column(style="white")
            for key, label in MENU:
                t.add_row(key, label)
            console.print(Panel(t, box=ROUNDED, border_style=MUTED, title="menu", padding=(1, 2)))
        else:
            print("\nMenu:")
            for key, label in MENU:
                print(f"  [{key}] {label}")
        choice = _ask("Choose").lower()
        if choice in ("q", "quit", "exit"):
            if RICH:
                console.print(f"[{MUTED}]bye 👋[/]")
            else:
                print("bye")
            return
        if choice == "1":
            check_health()
            render_workspaces(fetch_workspaces())
        elif choice == "2":
            ws = fetch_workspaces()
            render_workspaces(ws)
            if not ws:
                continue
            sel = _ask("Workspace number or id")
            iid = None
            if sel.isdigit() and 1 <= int(sel) <= len(ws):
                iid = ws[int(sel) - 1].get("id")
            elif sel:
                iid = sel
            if iid:
                show_workspace(iid)
        elif choice == "3":
            create_workspace_flow()
        elif choice == "4":
            check_health()
        else:
            _error("Unknown choice.")


# --- CLI entry ---------------------------------------------------------------
def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="cli.py",
        description="Premium terminal dashboard for the Receipt Spending Analyzer API.",
    )
    sub = parser.add_subparsers(dest="cmd")
    sub.add_parser("health", help="check API health")
    sub.add_parser("workspaces", help="list workspaces")
    p_show = sub.add_parser("show", help="show a workspace dashboard")
    p_show.add_argument("instance_id")
    sub.add_parser("menu", help="interactive dashboard (default)")

    args = parser.parse_args(argv)

    try:
        if args.cmd == "health":
            ok = check_health()
            sys.exit(0 if ok else 1)
        elif args.cmd == "workspaces":
            banner()
            render_workspaces(fetch_workspaces())
        elif args.cmd == "show":
            banner()
            show_workspace(args.instance_id)
        else:
            menu()
    except KeyboardInterrupt:
        if RICH and console:
            console.print(f"\n[{MUTED}]interrupted[/]")
        else:
            print("\ninterrupted")
        sys.exit(130)


if __name__ == "__main__":
    main()
