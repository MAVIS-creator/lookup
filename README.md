# Phone Intel Console

A portable, dependency-free phone intelligence application with a modern web interface.

It runs on Python standard library only and provides:
- Phone normalization and metadata heuristics
- Community risk reporting (spam, scam, safe, other)
- Retention-aware lookup history in SQLite
- A clean browser UI for lookups, reports, and history

## Preview

- Local API host: http://127.0.0.1:8080
- Web UI: http://127.0.0.1:8080

## Why This Project

This app is built for portability and fast local execution:
- No package installation required
- No framework lock-in
- Easy to copy and run across Windows environments
- Clear module boundaries for extension

## Project Structure

- [main.py](main.py): minimal app entrypoint
- [app/server.py](app/server.py): HTTP server and endpoint routing
- [app/service.py](app/service.py): business logic and risk scoring
- [app/storage.py](app/storage.py): SQLite persistence and retention
- [app/phone_utils.py](app/phone_utils.py): normalization and heuristics
- [app/config.py](app/config.py): runtime settings
- [web/index.html](web/index.html): app UI shell
- [web/style.css](web/style.css): full styling and responsive layout
- [web/app.js](web/app.js): frontend logic and API integration

## Endpoints

- GET /api/health
- POST /api/lookup
- POST /api/report
- GET /api/history

## Run Locally

1. Open terminal in the project root.
2. Run:

    python .\main.py

3. Open your browser:

    http://127.0.0.1:8080

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

## Data Retention

- Lookups are stored in SQLite at startup path configured in [app/config.py](app/config.py).
- Expired records are purged automatically when the server starts.
- Retention defaults are managed in [app/storage.py](app/storage.py).

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

## Roadmap

- CSV export for lookup history
- Theme switcher with persisted preference
- Optional local auth gate for admin actions
- SQLite backup and restore helpers

## License

Use this project responsibly and in compliance with your local laws and privacy requirements.
