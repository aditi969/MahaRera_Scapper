# RERA INSIGHT
### Maharashtra Real Estate Data Intelligence Platform

A high-performance, enterprise-grade data intelligence platform designed to systematically collect, validate, normalize, store, and analyze publicly accessible Maharashtra Real Estate Regulatory Authority ([MahaRERA](https://maharera.maharashtra.gov.in)) project registrations.

---

## 1. Platform Overview

**RERA Insight** transforms raw, unstructured, image-based, and PDF-embedded regulatory filings from the official MahaRERA registry into structured, relational, high-integrity real estate intelligence.

```
       MahaRERA Public Portal
                 │
                 ▼
     [Selenium Scraping Engine]  ─── Direct URL Pagination & Headless Chrome
                 │
                 ▼
      [Extraction & Parsing]    ─── BeautifulSoup HTML + PyMuPDF / Tesseract OCR
                 │
                 ▼
     [Validation & Cleansing]   ─── Maharashtra BBox, Regex ID, Deduplication
                 │
                 ▼
       [Database Storage]       ─── PostgreSQL (PL/pgSQL triggers) / SQLite Fallback
                 │
                 ▼
      [FastAPI REST & WS API]   ─── Analytical Aggregations & Sub-Second WebSocket Streaming
                 │
                 ▼
     [Next.js 14 App Router]    ─── Dashboard, Map Explorer, Scraper Console, Audits
```

### Key Capabilities
- **Searchable Project Explorer**: Real-time debounced query search across project names, promoter identities, and RERA IDs (`P520...`) with district, status, and typology filtering.
- **Project Deep-Dive Profiles**: Comprehensive 360° dossiers displaying building footprints, apartment inventories, bank escrow accounts, and parsed certificate commencement/completion timelines.
- **Geographic Map Visualization**: Full Maharashtra interactive Leaflet map rendering validated geographic coordinates with custom status-coded cluster pins.
- **Interactive Recharts Analytics**: Dynamic charts computing real-time distributions, project type allocations, registration velocity timelines, and revised completion dates.
- **Scraper Control Center & Live Telemetry**: Complete orchestration console allowing users to select districts, page boundaries, worker concurrency, and monitor execution progress via real-time WebSockets (`/ws/scraper`).
- **Data Quality & Schema Integrity Audits**: Automated field-level completeness audits, certificate OCR extraction benchmarks, and boundary checks.
- **System Health Diagnostics**: Live polling telemetry monitoring API latencies, database connectivity, and engine states.

---

## 2. Technology Stack

| Layer | Technologies | Justification |
|---|---|---|
| **Frontend** | **Next.js 14 (App Router)**, **React 18**, **TypeScript**, **Tailwind CSS**, **Recharts**, **Leaflet** | Clean enterprise light SaaS theme, server/client hybrid rendering, robust typing, and dynamic spatial mapping. |
| **Backend** | **Python 3.11+**, **FastAPI**, **Pydantic v2**, **SQLAlchemy 2.0**, **WebSockets**, **Uvicorn** | High-concurrency async endpoints, automated OpenAPI documentation, strict validation, and WebSocket broadcasting. |
| **Database** | **PostgreSQL** (with **PL/pgSQL** triggers and `JSONB`) / **SQLite** (local developer zero-friction fallback) | Relational integrity with JSON document flexibility for variable apartment and building layouts. |
| **Scraper** | **Selenium 4**, **BeautifulSoup 4**, **PyMuPDF (fitz)**, **Pillow / OpenCV**, **Tesseract OCR** | Faithfully refactored from the verified `RERA_Scrapping_fixed_v3.ipynb` notebook pipeline. |

---

## 3. Repository Structure

```
scarpping/
├── ARCHITECTURE.md                  # Comprehensive architectural specification
├── MASTER_PROMPT.md                 # System requirements and technical mandates
├── README.md                        # Documentation and quickstart guide
├── alembic.ini                      # Database migration configuration
├── rera_insight.db                  # Local database seeded with genuine Raigarh records
├── database/
│   ├── schema/
│   │   ├── 01_tables.sql            # DDL for PostgreSQL tables and indexes
│   │   └── 02_triggers_and_views.sql # PL/pgSQL triggers and analytical views
│   ├── migrations/                  # Alembic migration revisions
│   └── seeds/
│       └── import_raigarh_initial.py # Ingestion pipeline for genuine scraped data
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI application entrypoint & CORS
│   │   ├── core/config.py           # Environment and application settings
│   │   ├── database/session.py      # SQLAlchemy session & database engine
│   │   ├── models/models.py         # Declarative ORM models (Project, ScrapeJob, ScrapeLog)
│   │   ├── schemas/schemas.py       # Pydantic schemas for requests and responses
│   │   ├── repositories/            # Data access layer (project & scraper repositories)
│   │   ├── services/                # Business logic, background worker, WebSockets
│   │   └── api/routes/              # REST & WebSocket route handlers
│   └── tests/
│       └── test_api.py              # Automated pytest test suite (100% pass)
├── frontend/
│   ├── app/
│   │   ├── page.tsx                 # Overview Dashboard
│   │   ├── projects/page.tsx        # Project Explorer table with filters
│   │   ├── projects/[reraId]/page.tsx # Detailed Project Profile & Map
│   │   ├── analytics/page.tsx       # Interactive Recharts analytics
│   │   ├── map/page.tsx             # Interactive Maharashtra Leaflet map
│   │   ├── scraper/page.tsx         # Scraper Control Center & Live Logs
│   │   ├── data-quality/page.tsx    # Data Quality & Integrity Audits
│   │   └── system/page.tsx          # System Status & Service Health
│   ├── components/                  # Reusable UI, Layout, and Map components
│   ├── lib/api.ts                   # Typed API client connecting to backend
│   └── types/index.ts               # Shared TypeScript data models
└── scraper/
    ├── RERA_Scrapping_fixed_v3.ipynb # Original source notebook (preserved)
    ├── run_standalone.py            # CLI entrypoint for headless scraping
    └── core/                        # Modularized extraction engine
        ├── config.py                # Scraper runtime parameters
        ├── logger.py                # Thread-safe logging with WebSocket callbacks
        ├── checkpoint.py            # Deduplication cache & checkpointing
        ├── browser.py               # Headless Chrome manager with anti-detect flags
        ├── navigation.py            # Direct URL pagination & dropdown handlers
        ├── captcha.py               # Grayscale thresholding & OCR fallback
        ├── certificate.py           # PyMuPDF digital stream & date parser
        ├── extractor.py             # 53 standard fields & BHK modal extractor
        ├── csv_writer.py            # Schema normalization & 32k character splitter
        └── worker.py                # Multithreaded orchestration worker
```

---

## 4. Quickstart Guide (Local Execution)

No Docker or external cloud services are required. The entire stack runs seamlessly on any Windows machine.

### Method A: One-Click Launch (Recommended)

1. **Install Prerequisites** (First Time Only):
   - Double-click **`setup_dependencies.bat`** (or run `pip install -r requirements.txt` and `cd frontend && npm install`).
2. **Start the Application**:
   - Double-click **`start_all.bat`**.
   - This automatically starts the **FastAPI Backend (Port 8000)**, the **Next.js Frontend (Port 3000)**, and opens your browser at `http://localhost:3000`.

---

### Method B: Manual Startup (2 Command Windows)

#### Terminal 1 — Backend API (FastAPI)
```bash
# In the project root:
run_backend.bat
# Or using Python:
python run_backend.py
```
- API Docs: `http://127.0.0.1:8000/docs`
- Health check: `http://127.0.0.1:8000/api/health`

#### Terminal 2 — Frontend UI (Next.js)
```bash
# In the project root:
run_frontend.bat
# Or manually:
cd frontend
npm run dev
```
- Web Application: `http://localhost:3000`

---

### Step 2: Frontend Setup & Startup

```bash
# Open a second terminal in the project root
cd frontend

# Install npm packages
npm install

# Start the development server
npm run dev
```
The frontend application is now accessible at `http://localhost:3000`.

To create an optimized production build:
```bash
cd frontend
npm run build
npm start
```

---

### Step 3: Verified Initial Dataset

The platform comes pre-seeded with **10 genuine MahaRERA project records** directly scraped from Raigarh District (Page 1) on 13 November 2026:
- `P52000000003` - THE ADDRESS (Ongoing, Karjat)
- `P52000000480` - Delta Tower (Ongoing, Panvel)
- `P52000000007` - TULSI RESIDENCY (Ongoing, Panvel)
- `P52000000208` - GOKUL RESIDENCY (Ongoing, Panvel)
- `P52000007338` - VANDANA APARTMENT (Ongoing, Alibag)
- `P52000000270` - SHREE CHHAPATI SHIVAJI MAHARAJ SMRUTI COMPLEX (Ongoing, Mahad)
- `P52000000062` - DHEERAJ RESIDENCY (Ongoing, Panvel)
- `P52000004099` - SURABHI HERITAGE (Ongoing, Panvel)
- `P52000000721` - LAXMI RESIDENCY (Ongoing, Khalapur)
- `P52000006083` - SAI ANGAN (Ongoing, Panvel)

To re-seed or verify the database at any time:
```bash
python database/seeds/import_raigarh_initial.py
```

---

## 5. Running the Scraper

You have two ways to execute scraping jobs:

### Method A: Interactive Web UI (Recommended)
1. Navigate to `http://localhost:3000/scraper`.
2. Select your target district (e.g., *Raigarh (520)*), page boundaries (e.g. Page 1 to Page 1), concurrency, and headless mode.
3. Click **"Launch Scraper Job"**.
4. Watch real-time task logs, active status indicators, and extracted counts streamed live via WebSockets.

### Method B: Headless Standalone CLI
Run the command-line utility for manual, automated, or cron-triggered scraping:
```bash
python scraper/run_standalone.py --district Raigarh --district-code 520 --start-page 1 --end-page 1 --workers 2 --headless
```

---

## 6. Testing & Quality Assurance

The application includes an automated test suite verifying database initialization, filtering, detail retrieval, analytics aggregations, data quality audits, and job lifecycles:

```bash
# Run backend pytest suite
pytest backend/tests/test_api.py -v
```
**Test Result**: 6/6 tests passing (100% test pass rate in < 1 second).

---

## 7. PostgreSQL Production Deployment (Optional)

While SQLite is configured by default for effortless zero-setup local execution, switching to production PostgreSQL is fully supported:

1. Update `.env` (or pass environment variables):
   ```ini
   DATABASE_URL=postgresql://postgres:password@localhost:5432/rera_insight
   ```
2. Apply the PostgreSQL DDL and PL/pgSQL triggers:
   ```bash
   psql -U postgres -d rera_insight -f database/schema/01_tables.sql
   psql -U postgres -d rera_insight -f database/schema/02_triggers_and_views.sql
   ```
   Or run Alembic migrations:
   ```bash
   alembic upgrade head
   ```

---

## 8. License & Compliance
This software processes publicly accessible regulatory information under MahaRERA public domain policies for analytical transparency and compliance monitoring.


Backend:

cd "D:\Rera Web App\scarpping\scarpping"
.\run_backend.bat


Frontend:

cd "D:\Rera Web App\scarpping\scarpping"
.\run_frontend.bat

