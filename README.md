# NetPulse Development Package

**Project title:** NetPulse: A Web-Based Intelligent Network Monitoring, Performance Analytics, and Security Assessment System

This package is the implementation blueprint for the CCS 234 Networking and Communications final project. Build the application in checkpoint order. Do not skip the acceptance criteria.

## Package contents

- `SRS.md` — software requirements, scope, constraints, and quality requirements.
- `design/ARCHITECTURE.md` — architecture, components, data flow, and deployment.
- `design/USE_CASES_AND_FLOWS.md` — actors, use cases, and Mermaid diagrams.
- `design/DATABASE_ERD.md` — relational schema and ERD.
- `design/API_SPECIFICATION.md` — proposed REST and WebSocket contracts.
- `checkpoints/00_PROJECT_RULES_AND_SETUP.md` — global instructions and repository setup.
- `checkpoints/01_FOUNDATION_AND_DASHBOARD.md` — frontend/backend/database foundation.
- `checkpoints/02_NETWORK_INFORMATION_AND_DISCOVERY.md` — local network information and device discovery.
- `checkpoints/03_CONNECTIVITY_AND_DEVICE_MONITORING.md` — ping, packet loss, status, and monitoring.
- `checkpoints/04_PERFORMANCE_ANALYTICS.md` — latency statistics, jitter, history, and health score.
- `checkpoints/05_SECURITY_ASSESSMENT.md` — authorized TCP port checks and recommendations.
- `checkpoints/06_DIAGNOSTICS_REPORTS_AND_TOPOLOGY.md` — diagnostic engine, reports, and logical topology.
- `checkpoints/07_INTEGRATION_TESTING_AND_RELEASE.md` — integration, evaluation, documentation, and release.
- `testing/TEST_PLAN.md` — test cases and evaluation evidence.

## How to use the files

1. Read `SRS.md` and `checkpoints/00_PROJECT_RULES_AND_SETUP.md` first.
2. Start a new coding session with the global project rules and the next checkpoint file.
3. Complete only that checkpoint. Ask the coding assistant to inspect the current repository before changing anything.
4. Run the checkpoint's tests and verify every acceptance criterion.
5. Commit or back up the working project before moving to the next checkpoint.
6. Provide the next checkpoint file in the next coding session.

## Recommended technology stack

- Frontend: React + TypeScript + Vite
- Styling: Tailwind CSS
- Charts: Chart.js or Recharts
- Backend: Python + FastAPI
- Persistence: SQLite + SQLAlchemy
- Network operations: Python standard library, platform ping utility, and optional Scapy
- PDF: ReportLab
- Testing: Pytest and frontend test tooling

Keep the first release local-first. Do not add cloud hosting, machine learning, user accounts, or unrelated features unless the instructor specifically requires them.

## Important safety and accuracy rules

- Only discover or test networks and devices that the operator owns or is authorized to assess.
- Restrict scanning to the detected local subnet by default. Require explicit confirmation before scanning a different range.
- Do not perform exploit attempts, vulnerability exploitation, credential guessing, or stealth scanning.
- A TCP port accepting a connection is not proof of a vulnerability. Describe it as an exposed or open service requiring review.
- A failed ping does not prove that a device is offline; ICMP may be blocked. Display the observation as `Unreachable / No ICMP response`, not as a definitive offline verdict.
- Never fabricate MAC addresses, hostnames, latency, packet loss, topology links, or security findings.
- If a value cannot be measured, represent it as unavailable (`null` / `N/A`), not zero.
- Keep network operations bounded by timeouts, concurrency limits, and a configurable scan range.
- Display permission and platform limitations clearly.

## Definition of done

A checkpoint is complete only when:
- Its acceptance criteria pass.
- The application still starts.
- Existing completed features continue to work.
- No placeholder controls falsely claim to perform an action.
- Errors and permission failures are handled visibly.
- Setup and usage instructions are updated.

---

# NetPulse implementation

This repository now contains the completed checkpoint 00–07 implementation: a React + TypeScript frontend and a FastAPI + SQLAlchemy/SQLite backend. The application is local-first and runs entirely on the operator's machine.

## Current status

| Area | Status |
|---|---|
| Backend API and SQLite persistence | Implemented and tested |
| Local network information and bounded discovery | Implemented and tested |
| Ping, packet loss, monitoring and WebSocket/polling updates | Implemented and tested |
| Analytics, latency history, jitter, availability and health score | Implemented and tested |
| Authorized TCP service assessment, findings and recommendations | Implemented and tested |
| Diagnostics, PDF/CSV reports, report downloads and logical topology | Implemented and tested |
| Automated backend tests | **82 passed** (`pytest`) |
| Automated frontend tests | **18 passed** (`vitest`) |
| Frontend production build | Passes (`tsc --noEmit && vite build`) |

Verified on Windows 11 with Python 3.11.9, Node.js 24.14.0 and npm 11.9.0. Linux and macOS were not verified.

## Prerequisites

- Windows PowerShell 5.1 or later (commands below use PowerShell).
- Python 3.11 or later.
- Node.js 20 or later, with npm.
- A local network interface and permission to run the operating system's `ping` utility.
- Authorization to observe the local subnet and any devices you assess.

## Install and start (Windows PowerShell)

Run the commands from the repository root:

```powershell
# 1. Backend setup
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cd ..

# 2. Optional local configuration
Copy-Item .env.example .env
Copy-Item frontend\.env.example frontend\.env

# 3. Start the backend in one terminal
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

The API is then available at `http://127.0.0.1:8000`, with interactive documentation at `http://127.0.0.1:8000/docs`.

```powershell
# 4. Start the frontend in a second terminal
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

The frontend reads `VITE_API_BASE_URL`. The default in `frontend/.env.example` is `http://127.0.0.1:8000`. If you change the backend port, update `frontend/.env` and restart Vite.

## Run from VS Code

The repository ships a `.vscode/` folder, so no manual terminal setup is required once the dependencies are installed.

1. Open the repository folder in VS Code (`File > Open Folder`).
2. When prompted, install the recommended extensions. The Python extension must use `backend/.venv/Scripts/python.exe`; `.vscode/settings.json` already selects it.
3. On first use, run **Terminal > Run Task > Setup: Install everything**.
4. Run **Terminal > Run Task > Run: Full stack (backend + frontend)**. This opens both servers in separate terminal panels and prints the URLs.
5. Open `http://localhost:5173`. The API is at `http://127.0.0.1:8000` and its interactive docs at `http://127.0.0.1:8000/docs`.

Alternatively, press `F5` and choose **NetPulse: Full stack (debug)** to start both servers under the debugger.

Other ready-made tasks (all under **Terminal > Run Task**):

| Task | What it does |
|---|---|
| `Backend: Run API` | Starts Uvicorn with auto-reload on port 8000 |
| `Frontend: Run dev server` | Starts Vite on port 5173 |
| `Test: Backend (pytest)` | Runs the backend test suite |
| `Test: Frontend (vitest)` | Runs the frontend test suite |
| `Build: Frontend (typecheck + bundle)` | Runs `tsc --noEmit && vite build` |
| `Setup: Install everything` | Creates/updates Python and Node dependencies |

Notes:

- If a terminal already uses port 8000 or 5173, stop that process first. Find it with `Get-NetTCPConnection -LocalPort 8000` and stop it with `Stop-Process -Id <PID>`.
- The **Backend: Run API** task uses `--reload`. The **F5** debug configuration starts without reload so breakpoints work reliably; restart the debugger after backend edits.
- The recommended extensions are Python, Pylance, debugpy and Tailwind CSS IntelliSense. None are required to run the app from a terminal.

### Restricted PowerShell execution policy

If `Activate.ps1` is blocked, either allow scripts for the current user or call the virtual-environment interpreter directly:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
# or, without activation:
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

## Run the tests

```powershell
# Backend: isolated in-memory SQLite database per test
cd backend
.\.venv\Scripts\python.exe -m pytest -q

# Frontend
cd frontend
npm test
npm run build
```

Expected result at the time of writing:

```text
82 passed                       # backend
18 passed                       # frontend tests
tsc --noEmit && vite build      # succeeds with no warnings
```

The backend tests never use the developer database; `tests/conftest.py` creates an isolated in-memory database for every test.

## Configuration

Backend settings use the `NETPULSE_` prefix. Values may be set in the environment, in a root `.env` file, or in `backend/.env`. The frontend uses Vite variables in `frontend/.env`.

| Variable | Default | Purpose |
|---|---|---|
| `NETPULSE_DATABASE_URL` | `sqlite:///./data/netpulse.db` | SQLite database location |
| `NETPULSE_CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Allowed frontend origins |
| `NETPULSE_MAX_SCAN_HOSTS` | `256` | Maximum addresses considered per discovery scan |
| `NETPULSE_SCAN_CONCURRENCY` | `32` | Maximum concurrent discovery probes |
| `NETPULSE_PING_MAX_COUNT` | `20` | Maximum probes in one ping test |
| `NETPULSE_PING_MAX_TIMEOUT_MS` | `5000` | Maximum per-probe timeout |
| `NETPULSE_MONITORING_MIN_INTERVAL_SECONDS` | `5` | Minimum monitoring interval |
| `NETPULSE_SECURITY_TIMEOUT_MS` | `800` | TCP connection timeout |
| `NETPULSE_ALLOW_CUSTOM_SCAN_RANGE` | `false` | Keep discovery restricted to the detected local subnet |
| `NETPULSE_LOG_LEVEL` | `INFO` | Backend log level |
| `VITE_API_BASE_URL` | `http://127.0.0.1:8000` | Frontend API base URL |

The Settings page is read-only and shows the active backend values. It does not pretend to change backend configuration.

## Architecture at a glance

```text
frontend/ (React + TypeScript + Vite + Tailwind + Recharts)
  pages/        Overview, Discovery, Devices, Device detail, Analytics,
                Security, Diagnostics, Reports, Topology, Settings
  services/     typed REST client, WebSocket monitoring client
  hooks/        async request state
  lib/          null-safe formatting and chart transforms

backend/ (FastAPI + SQLAlchemy + SQLite)
  api/routes/   health, dashboard, network, devices, monitoring,
                analytics, security, diagnostics, reports
  api/websocket.py
                /ws/monitoring live observation events
  services/     network info, discovery, connectivity, monitoring,
                analytics, security, diagnostics, reports
  models/       SQLAlchemy entities
  schemas/      Pydantic request/response contracts
  database/     engine, session, UTC helpers
```

All timestamps are stored as naive UTC in SQLite and serialized by the API with an explicit `Z`. Missing measurements are `null` in JSON and render as `N/A` in the UI.

### API summary

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/health` | Service, version, database status and timestamp |
| `GET` | `/api/dashboard/summary` | Dashboard totals, health score and recent activity |
| `GET` | `/api/network/info` | Interfaces, local IPv4, subnet, gateway and candidates |
| `POST` | `/api/network/scan` | Authorized bounded discovery; local subnet by default |
| `GET` | `/api/network/topology` | Logical host/gateway/device view with inferred edges |
| `GET` | `/api/devices` | Device inventory with latest observation |
| `GET` | `/api/devices/{id}` | Device detail, recent pings, monitoring and scans |
| `POST` | `/api/devices/{id}/ping` | Bounded ICMP probe test and statistics |
| `POST` | `/api/monitoring/start` | Start a bounded monitoring session |
| `GET` | `/api/monitoring` | List monitoring sessions |
| `GET` | `/api/monitoring/{id}` | Session status and observations |
| `POST` | `/api/monitoring/{id}/stop` | Stop a session cleanly |
| `GET` | `/api/analytics/summary` | Latency, loss, jitter, availability and health inputs |
| `GET` | `/api/analytics/history` | Time-windowed samples for charts |
| `GET` | `/api/security/profiles` | Allowlisted port profiles |
| `POST` | `/api/security/scan` | Authorized TCP connect checks against allowlisted ports |
| `GET` | `/api/security/scans` | Assessment history |
| `GET` | `/api/security/findings` | Observed port states and recommendations |
| `GET` | `/api/diagnostics/recommendations` | Deterministic rule-based guidance |
| `POST` | `/api/reports/generate` | Generate a PDF or CSV report from stored data |
| `GET` | `/api/reports` | Report history |
| `GET` | `/api/reports/{id}/download` | Download a report by ID; paths are never client-supplied |
| `WS` | `/ws/monitoring` | Live monitoring observation events |

## Safety, accuracy and feature boundaries

- **Local-first only.** There is no authentication, cloud service, telemetry, AI/ML inference, exploitation, credential testing, stealth scanning or evasion.
- **Discovery scope is enforced server-side.** The default and only normal scope is the detected private local subnet. A different CIDR requires the documented configuration switch and explicit authorization confirmation.
- **Network work is bounded.** Discovery has host, concurrency and timeout limits. Ping count/timeout, monitoring interval/device count and TCP check timeouts/concurrency are validated by the backend.
- **Port checks are not vulnerability scans.** An open port is recorded as an observation. Service names such as HTTP or SSH are conventional labels and are not verified by banner grabbing.
- **A failed ping is not proof of an offline device.** The UI reports `No ICMP response`, because firewalls and client isolation can block ICMP.
- **No fabricated operational data.** MAC addresses, hostnames, latency, packet loss, topology links and findings are recorded only when observed. Missing values are `N/A`/`null`, never zero.
- **Health score is indicative.** It uses the documented 40% latency, 35% packet loss and 25% availability weights with step thresholds. It is `null` and labelled `Insufficient data` when required inputs are absent.
- **Monitoring is in-process.** A restart marks stale sessions as `interrupted`. The UI claims “live” only when the WebSocket is connected and also polls every five seconds while a session is running.
- **Report files are contained.** Reports are written to the configured reports directory and downloaded by database ID. Traversal attempts return `404`.
- **Errors are visible.** API failures and permission problems are rendered in the UI with a code and retry action; validation and authorization failures use consistent JSON error bodies.

## Local data and reset

- Database: `backend/data/netpulse.db`
- Reports: `backend/data/reports/`
- Logs: written to the console by default; set `NETPULSE_LOG_LEVEL` to adjust verbosity.
- To reset the local installation, stop the backend and delete `backend/data/`. Both the database and generated reports are excluded from version control by `.gitignore`.

## Checkpoint compliance

| Checkpoint | Implemented evidence |
|---|---|
| 00 — Rules and setup | Repository structure, `.gitignore`, `.env.example`, README instructions, no secrets |
| 01 — Foundation and dashboard | FastAPI app, SQLite models, dashboard summary, React shell, health indicator |
| 02 — Network information and discovery | Interface/route detection, private-subnet scope enforcement, bounded ping sweep + OS neighbour observations |
| 03 — Connectivity and monitoring | Ping statistics, `No ICMP response` semantics, monitoring sessions, WebSocket + polling fallback |
| 04 — Performance analytics | Latency history, min/max/average, packet loss, jitter, availability, weighted health score |
| 05 — Security assessment | Allowlisted TCP checks, authorization gate, open-port observations, review recommendations |
| 06 — Diagnostics, reports and topology | Rule-based diagnostics, PDF/CSV generation, controlled downloads, logical topology |
| 07 — Integration and release | 82 backend tests, 18 frontend tests, build, live integration checks, test evidence and documentation |

Executed integration evidence is recorded in [`testing/INTEGRATION_EVIDENCE_2026-11-15.md`](testing/INTEGRATION_EVIDENCE_2026-11-15.md).

## Known limitations

- ICMP may be blocked by host firewalls or client isolation, so some reachable devices can appear as `No ICMP response` or may not be discovered at all.
- MAC addresses and hostnames come from the operating system neighbour cache and may be unavailable or incomplete.
- Discovery is capped by `NETPULSE_MAX_SCAN_HOSTS`; larger subnets are truncated and the UI/API reports a warning.
- Only Windows 11 was exercised. Linux and macOS support was not verified.
- The security assessment tests only the configured allowlist with plain TCP connection attempts. It does not identify application versions, vulnerabilities or credentials.
- SQLite and the built-in background task model target a single local user, not concurrent multi-user deployment.
- The production build splits React and Recharts into separate vendor chunks; the chart chunk is roughly 400 kB and loads only on pages that render charts.
- The Settings page is intentionally read-only. Backend changes require editing environment variables and restarting the backend.

## Suggested demonstration sequence

1. Start the backend and frontend with the commands above.
2. Open the Overview and show the detected network context and health state.
3. Run a discovery scan and open a discovered device.
4. Run a ping test and show latency, packet loss and jitter.
5. Start monitoring and show a new observation arriving.
6. Open Analytics and show the latency history and health inputs.
7. Run an authorized TCP assessment and inspect an open-port observation.
8. Open Diagnostics and explain that recommendations are rule-based, not root-cause claims.
9. Generate a PDF report, then a CSV export, and open the PDF.
10. Open Topology, explain the inferred logical view, and finish with the documented limitations.

## Repository layout

```text
NetPulse_Development_Package/
├── README.md
├── SRS.md
├── CHECKPOINT_INDEX.md
├── .env.example
├── .gitignore
├── .vscode/                     tasks, debug configs, recommended extensions
├── checkpoints/                 00–07 specification files
├── design/                      architecture, use cases, ERD, API specification
├── testing/                     test plan and executed integration evidence
├── backend/
│   ├── requirements.txt
│   ├── pytest.ini
│   ├── app/                     FastAPI application, models, schemas, services, routes
│   ├── tests/                   pytest suite
│   └── data/                    local SQLite database and reports (ignored)
└── frontend/
    ├── package.json
    ├── package-lock.json
    ├── vite.config.ts
    ├── src/                     React app, pages, components, services, tests
    └── dist/                    production build output (ignored)
```
