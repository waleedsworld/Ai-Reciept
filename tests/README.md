# Test suite

Automated tests for the Receipt Spending Analyzer. They run fully offline —
the OpenAI-backed paths (receipt parsing, advice, chat) are mocked, so **no
`OPENAI_API_KEY` is required**.

## Running

```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt pytest
python -m pytest
```

## What's covered

| File | Area |
| --- | --- |
| `test_health.py` | health endpoint, landing/upload pages |
| `test_workspace.py` | workspace create / list / get / update / delete + auth |
| `test_categories.py` | category init / add / rename / delete + validation |
| `test_transactions.py` | transaction listing, budget upsert & utilisation |
| `test_reports.py` | period reports, custom ranges, chart data, CSV export |
| `test_aggregators.py` | unit tests for the pure DataFrame aggregators |
| `test_insights.py` | AI advice + chat endpoints (OpenAI client mocked) |
| `test_e2e.py` | full journey: workspace → categories → upload → report |

## Isolation

`conftest.py` chdirs each test into a fresh `tmp_path` and lays down the
`storage/` skeleton, so tests never touch real data and never leak state.

## Known issues surfaced by the suite

`test_list_multiple_workspaces_per_user` is marked `xfail` (strict): the app's
`list_workspaces` currently 500s once a single user owns two or more
workspaces because it mixes tz-aware and tz-naive timestamps. The xfail keeps
the regression documented until the endpoint is fixed.
