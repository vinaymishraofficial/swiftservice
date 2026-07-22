<p align="center">
  <img src="./swiftservice/public/logo-white.svg" alt="SwiftService Logo" width="120" />
</p>

# SwiftService

SwiftService is an open-source field service management app for Frappe and ERPNext.
It helps service teams run the full service lifecycle from complaint registration to engineer dispatch, on-site resolution, parts management, billing, and closure.

Designed for fast-moving service operations, SwiftService combines a Frappe backend with a dedicated Vue + `frappe-ui` frontend, optimized for both office users and field engineers.

## What SwiftService Solves

- Tracks service requests with complete customer and product context
- Assigns engineers and manages visit planning and follow-up visits
- Supports GPS check-in/check-out, customer pinning, and navigation
- Handles diagnosis, spare part demand, repair, replacement, and return flows
- Connects with ERPNext for inventory movement, invoicing, and payment records

## Highlights

- Single-page app route: `/swiftservice`
- Mobile-friendly engineer workflows
- GPS-based visit check-in / check-out
- Customer pin + navigation support
- Live tracking foundation (periodic live location push + ETA APIs)
- ERPNext integration for stock, invoicing, and payment flows

## End-to-End Service Flow

```mermaid
flowchart TD

%% ===========================
%% SALES & INSTALLATION
%% ===========================

A[Product Sold] --> B[Sales Order / Delivery]
B --> C[Installation Note]
C --> D[Installed Base<br/>Customer + Item + Serial Number]

%% ===========================
%% CUSTOMER COMPLAINT
%% ===========================

D --> E{Product Status}

E -->|Warranty Active| F[Customer Raises Complaint]
E -->|AMC Active| F
E -->|Warranty Expired| F

F --> G[Create Service Request / Issue]
G --> H[Validate Warranty / AMC / SLA]
H --> I[Fetch Service History]
I --> J[Service Coordinator Review]

%% ===========================
%% ASSIGNMENT
%% ===========================

J --> K{Coordinator Decision}

K -->|Assign Engineer| L[Engineer Assignment]
K -->|Need More Information| M[Request Customer Details]
M --> J

L --> N[Visit Planning]
N --> O[Customer Visit Confirmation]
O --> P[Engineer Check-In]
P --> Q[Inspection & Diagnosis]

%% ===========================
%% DIAGNOSIS
%% ===========================

Q --> R{Diagnosis Result}

%% Fixed
R -->|Issue Fixed| S[Repair Completed]

%% Spare Required
R -->|Spare Required| T[Create Spare Request]

%% Factory Repair
R -->|Factory Repair| U[Initiate RMA]

%% Replacement
R -->|Replacement Required| V[Replacement Approval]

%% No Fault
R -->|No Fault Found| W[Close with Report]

%% ===========================
%% SPARE REQUEST
%% ===========================

T --> X[Store Verification]

X --> Y{Stock Available?}

Y -->|Yes| Z[Issue Spare Parts]

Y -->|No| AA[Purchase Request]
AA --> AB[Purchase Order]
AB --> AC[Purchase Receipt]
AC --> Z

Z --> AD[Engineer Receives Spare]
AD --> AE[Repair Product]
AE --> S

%% ===========================
%% FACTORY REPAIR
%% ===========================

U --> AF[Pickup Machine]
AF --> AG[Receive at Factory]
AG --> AH[Quality Inspection]
AH --> AI[Repair Job]
AI --> AJ[Testing]
AJ --> AK[Dispatch to Customer]
AK --> S

%% ===========================
%% REPLACEMENT
%% ===========================

V --> AL[Management Approval]
AL --> AM[Replacement Challan]
AM --> AN[Dispatch New Product]
AN --> AO[Receive Old Product]
AO --> AP[Serial Number Mapping]
AP --> AQ[Warranty Transfer]
AQ --> S

%% ===========================
%% CLOSURE
%% ===========================

S --> AR[Customer Verification]
W --> AR

AR --> AS[Generate Service Report]

AS --> AT{Chargeable?}

AT -->|Yes| AU[Sales Invoice]
AT -->|No| AV[Free Warranty Service]

AU --> AW[Customer Feedback]
AV --> AW

AW --> AX[Close Service Request]

%% ===========================
%% PREVENTIVE MAINTENANCE
%% ===========================

D --> BA[Maintenance Schedule]
BA --> BB[Auto Generate Visit]
BB --> BC[Assign Engineer]
BC --> BD[Preventive Maintenance Visit]
BD --> BE[Checklist]
BE --> BF[Calibration]
BF --> BG[PM Report]
BG --> BH[Schedule Next Visit]
```

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

## Community

- [Contributing Guide](./CONTRIBUTING.md)
- [Code of Conduct](./CODE_OF_CONDUCT.md)
- [Security Policy](./SECURITY.md)

## Notes

- This repo intentionally ignores `frontend/node_modules` and built frontend output.
- Commit source only; generated assets are rebuilt per environment.

## License

GNU General Public License v3.0 (`GPL-3.0`)

See [LICENSE](./LICENSE) for the full text.
