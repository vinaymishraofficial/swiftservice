# SwiftService

SwiftService is a field-service operations app for Frappe/ERPNext with a dedicated Vue + `frappe-ui` frontend.

It covers service requests, engineer assignment, engineer visits, diagnosis, spare flow, repair workflow, reporting, billing, and closure.

## Highlights

- Single-page app route: `/swiftservice`
- Mobile-friendly engineer workflows
- GPS-based visit check-in / check-out
- Customer pin + navigation support
- Live tracking foundation (periodic live location push + ETA APIs)
- ERPNext integration for stock, invoicing, and payment flows

## Tech Stack

- Backend: Frappe (Python)
- Frontend: Vue 3 + `frappe-ui`
- Map & Geocoding: Google Maps API (preferred), OSM fallback

## Repository Structure

```text
apps/swiftservice/
├── swiftservice/                # Python app (doctypes, APIs, hooks)
├── frontend/                    # Vue frontend source
│   ├── src/
│   └── package.json
├── pyproject.toml
└── README.md
```

## Prerequisites

- Frappe Bench (v16 compatible)
- Node.js + Yarn
- Python 3.14 (as configured in `pyproject.toml`)

## Setup

From your bench root:

```bash
bench get-app <repo_url>
bench install-app swiftservice --site <your-site>
```

## Frontend Build

```bash
cd apps/swiftservice/frontend
yarn install
yarn build
```

Then clear cache:

```bash
cd ~/frappe-bench
bench --site <your-site> clear-cache
```

## Configuration

Open **SwiftService Settings** and configure:

- Brand details (logo/favicon)
- ERP defaults (warehouse/income account/cost center)
- Google Maps API key (for geocoding + ETA/distance)

## Development Workflow

### Run checks

```bash
cd apps/swiftservice
pre-commit install
pre-commit run --all-files
```

Tools used:

- `ruff` (Python lint/format checks)
- `eslint` + `prettier` (frontend)
- `pyupgrade`

### Typical local cycle

```bash
# backend changes
bench restart

# frontend changes
cd apps/swiftservice/frontend && yarn build
bench --site <your-site> clear-cache
```

## Notes

- This repo intentionally ignores `frontend/node_modules` and built frontend output.
- Commit source only; generated assets are rebuilt per environment.

## License

MIT
