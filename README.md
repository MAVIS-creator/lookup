# Phone Intel Console

A portable, dependency-free phone intelligence application with a modern web interface.

It runs on Python standard library only and provides:
- Phone normalization and metadata heuristics
- Community risk reporting (spam, scam, safe, other)
- Retention-aware lookup history in SQLite
- A clean browser UI for lookups, reports, and history

## Current Scope

This project is a local-first phone intelligence console designed for:
- Fast local setup with zero third-party Python dependencies
- Safe metadata enrichment based on input heuristics
- Lightweight reputation scoring from user-submitted reports
- Data retention tracking with automatic expiry cleanup

This project does not include unauthorized private identity lookups or hidden data-source scraping.

## Preview

- Local API host: http://127.0.0.1:8080
- Web UI: http://127.0.0.1:8080

## Why This Project

This app is built for portability and fast local execution:
- No package installation required
- No framework lock-in
- Easy to copy and run across Windows environments
- Clear module boundaries for extension

## Complete Project Inventory

### Root Files

- [main.py](main.py): minimal app entrypoint
- [.gitignore](.gitignore): ignores local runtime artifacts such as SQLite DB and Python cache
- [README.md](README.md): full project documentation

### Backend Package

- [app/__init__.py](app/__init__.py): package marker and top-level package description
- [app/server.py](app/server.py): HTTP server and endpoint routing
- [app/service.py](app/service.py): business logic and risk scoring
- [app/storage.py](app/storage.py): SQLite persistence and retention
- [app/phone_utils.py](app/phone_utils.py): normalization and heuristics
- [app/config.py](app/config.py): runtime settings

### Frontend Files

- [web/index.html](web/index.html): app UI shell
- [web/style.css](web/style.css): full styling and responsive layout
- [web/app.js](web/app.js): frontend logic and API integration

### Runtime Artifacts

- phone_retention.db: SQLite database generated at runtime (ignored by Git)

## Feature Inventory

### Backend Features

- Threaded HTTP server with standard library only
- Static file hosting for frontend assets
- API routing for health, lookup, report, and history
- CORS support for local browser usage
- JSON request parsing and JSON responses
- Input validation and structured error responses
- Path traversal protection for static asset access
- Startup retention purge for expired lookup records

### Lookup Features

- Phone normalization into conservative E.164-like format
- Country inference by known prefix map
- Line type heuristic classification
- Risk score computation from lookup heuristics and report counts
- Persistent lookup history with timestamp and expiry tracking

### Reporting Features

- Report categories: spam, scam, safe, other
- Optional user note attached to a report
- Per-phone report aggregation and category counts
- Risk score influence from report patterns

### UI Features

- Responsive modern layout
- Styled cards for lookup, results, reporting, and history
- Live lookup rendering in metric cards
- Dynamic risk badge color states
- History table with refresh control
- Inline error and status messages
- Basic reveal animation and decorative gradient background

## Endpoints

- GET /api/health
- POST /api/lookup
- POST /api/report
- GET /api/history

## Endpoint Details

### GET /api/health

Purpose:
- Verify server availability

Response:

        {
            "status": "ok"
        }

### POST /api/lookup

Purpose:
- Normalize phone and compute metadata plus risk score
- Persist a lookup record

Request body:

        {
            "phone": "+2348012345678"
        }

Response shape:

        {
            "raw_phone": "+2348012345678",
            "normalized_phone": "+2348012345678",
            "country": {
                "code": "NG",
                "name": "Nigeria"
            },
            "line_type_guess": "mobile_or_fixed",
            "report_counts": {
                "spam": 0,
                "scam": 0,
                "safe": 0,
                "other": 0
            },
            "created_at": "2026-04-25T00:00:00+00:00",
            "risk_score": 5,
            "lookup_id": 1
        }

### POST /api/report

Purpose:
- Add a reputation report for a phone number

Request body:

        {
            "phone": "+2348012345678",
            "category": "spam",
            "note": "Repeated unsolicited calls"
        }

Response shape:

        {
            "report_id": 1,
            "normalized_phone": "+2348012345678",
            "report_counts": {
                "spam": 1,
                "scam": 0,
                "safe": 0,
                "other": 0
            }
        }

### GET /api/history

Purpose:
- Read lookup history
- Supports optional filters

Query params:
- phone: optional raw or normalized phone
- limit: optional integer, default 50, max 500

Example:

        GET /api/history?phone=%2B2348012345678&limit=25

Response shape:

        {
            "items": [
                {
                    "id": 1,
                    "raw_phone": "+2348012345678",
                    "normalized_phone": "+2348012345678",
                    "country_code": "NG",
                    "country_name": "Nigeria",
                    "line_type_guess": "mobile_or_fixed",
                    "risk_score": 5,
                    "created_at": "2026-04-25T00:00:00+00:00",
                    "expires_at": "2026-05-25T00:00:00+00:00"
                }
            ]
        }

## Run Locally

1. Open terminal in the project root.
2. Run:

    python .\main.py

3. Open your browser:

    http://127.0.0.1:8080

## Local Development Workflow

1. Start server with [main.py](main.py).
2. Open browser and perform a lookup.
3. Submit report categories to affect scoring.
4. Refresh history to inspect retained records.
5. Stop and restart server to verify startup purge behavior.

## API Quick Examples

Health check:

    GET /api/health

Lookup payload:

    {
      "phone": "+2348012345678"
    }

Report payload:

    {
      "phone": "+2348012345678",
      "category": "spam",
      "note": "Repeated unsolicited calls"
    }

History query:

    GET /api/history?phone=%2B2348012345678&limit=25

## Data Model Summary

### lookups table

Stored fields:
- id
- raw_phone
- normalized_phone
- country_code
- country_name
- line_type_guess
- risk_score
- created_at
- expires_at

### reports table

Stored fields:
- id
- normalized_phone
- category
- note
- created_at

## Data Retention

- Lookups are stored in SQLite at startup path configured in [app/config.py](app/config.py).
- Expired records are purged automatically when the server starts.
- Retention defaults are managed in [app/storage.py](app/storage.py).

## Scoring Model

Current risk score behavior in [app/service.py](app/service.py):
- Base score starts at 5
- short_or_special line type adds 10
- Each spam report adds 12
- Each scam report adds 20
- Each safe report subtracts 4
- Final score clamped between 0 and 100

## UI Highlights

- Responsive, card-based layout
- Animated visual treatment and soft-gradient background
- Live risk badge updates
- Inline error and report feedback
- History table with quick refresh

## Security Notes

- Path traversal protection is enforced for static file serving.
- Input validation is applied to phone input and report categories.
- This project intentionally uses safe metadata heuristics and community reports, not unauthorized private identity data.

## Portability Notes

- Uses only Python standard library modules
- No pip install step required
- Works as a simple folder copy between compatible Python environments
- Runtime DB file is local and self-contained

## Roadmap

- CSV export for lookup history
- Theme switcher with persisted preference
- Optional local auth gate for admin actions
- SQLite backup and restore helpers

## Troubleshooting

Server does not start:
- Confirm Python is available on PATH
- Confirm port 8080 is free or update host and port in [app/config.py](app/config.py)

UI loads but API calls fail:
- Confirm server is running from project root
- Test health endpoint in browser: http://127.0.0.1:8080/api/health

No history items appear:
- Run at least one lookup first
- Check if startup purge removed expired records

## License

Use this project responsibly and in compliance with your local laws and privacy requirements.
