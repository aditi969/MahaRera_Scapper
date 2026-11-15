# RERA INSIGHT
## Maharashtra Real Estate Data Intelligence Platform

Version: 1.0
Status: Architecture Definition
Primary Development Environment: Antigravity

---

# 1. PROJECT OVERVIEW

RERA Insight is a full-stack real-estate data intelligence platform built around structured data collected from the Maharashtra Real Estate Regulatory Authority (MahaRERA).

The platform transforms raw RERA website data into a searchable, validated, structured and visualized real-estate intelligence system.

The system is not designed as a simple scraping script or a generic dashboard.

The core pipeline is:

MahaRERA
    ↓
Scraping Engine
    ↓
Raw Data Extraction
    ↓
Data Cleaning
    ↓
Normalization
    ↓
Validation
    ↓
Duplicate Detection
    ↓
PostgreSQL
    ↓
FastAPI
    ↓
Next.js
    ↓
Search / Analytics / Map / Monitoring / Data Quality

The platform must preserve the reliability of the existing scraper while adding a professional application layer around it.

---

# 2. PROJECT OBJECTIVES

The system should provide:

1. Reliable MahaRERA data collection.
2. Structured PostgreSQL storage.
3. Searchable real-estate project records.
4. Project-level detailed information.
5. District-level analytics.
6. Registration and completion trends.
7. Project status analytics.
8. Interactive Maharashtra project map.
9. Scraper execution monitoring.
10. Live scraper progress.
11. Data quality monitoring.
12. Duplicate detection.
13. Validation status.
14. Source/evidence traceability.
15. Professional responsive UI.
16. Maintainable backend architecture.
17. Clear separation between scraping, processing, storage and presentation.

---

# 3. PRODUCT POSITIONING

Product Name:

RERA Insight

Primary Description:

Maharashtra Real Estate Data Intelligence Platform

The product should feel like a serious data product rather than:

- a college CRUD application
- a basic scraper
- a generic admin dashboard
- an AI chatbot
- a visualization-only project

The product should demonstrate:

Data Engineering
+
Web Scraping
+
Data Processing
+
Database Engineering
+
Backend API Engineering
+
Frontend Engineering
+
Analytics
+
Geospatial Visualization
+
Operational Monitoring

---

# 4. CORE PRINCIPLE

The project follows a deterministic-first architecture.

The system should prioritize:

Accuracy
Reliability
Traceability
Validation
Performance
Maintainability

over unnecessary complexity.

Do not introduce technology simply because it is popular.

---

# 5. TECHNOLOGY STACK

## Frontend

Next.js
TypeScript
React
Tailwind CSS
Framer Motion
Recharts
Leaflet / React Leaflet

## Backend

Python
FastAPI
Pydantic
SQLAlchemy
Alembic

## Database

PostgreSQL

## Database Procedural Logic

PL/pgSQL

Important:

Use PostgreSQL + PL/pgSQL.

Do NOT use Oracle PL/SQL.

## Scraping

Python
Selenium

Supporting extraction technologies may include:

PDF extraction
OCR
HTML parsing
Data normalization

depending on the existing scraper implementation.

## Communication

REST APIs
WebSockets for live scraper monitoring

## Development

Git
GitHub
Docker
Docker Compose where useful

---

# 6. HIGH-LEVEL SYSTEM ARCHITECTURE

```text
                         MAHARERA
                            │
                            ▼
                  ┌───────────────────┐
                  │  SCRAPING ENGINE  │
                  │     Selenium      │
                  └─────────┬─────────┘
                            │
                            ▼
                  ┌───────────────────┐
                  │   RAW EXTRACTION   │
                  │ HTML / PDF / OCR   │
                  └─────────┬─────────┘
                            │
                            ▼
                  ┌───────────────────┐
                  │ DATA PROCESSING    │
                  │                   │
                  │ Cleaning          │
                  │ Normalization     │
                  │ Validation        │
                  │ Deduplication     │
                  └─────────┬─────────┘
                            │
                            ▼
                  ┌───────────────────┐
                  │    POSTGRESQL     │
                  │                   │
                  │ Projects          │
                  │ Promoters         │
                  │ Buildings         │
                  │ Certificates     │
                  │ Scrape Jobs       │
                  │ Data Quality      │
                  └─────────┬─────────┘
                            │
                            ▼
                  ┌───────────────────┐
                  │      FASTAPI      │
                  │                   │
                  │ REST APIs         │
                  │ Analytics         │
                  │ Scraper Control   │
                  │ WebSockets        │
                  └─────────┬─────────┘
                            │
                 ┌──────────┴──────────┐
                 ▼                     ▼
        ┌─────────────────┐   ┌─────────────────┐
        │    NEXT.JS      │   │  WEBSOCKET      │
        │    FRONTEND     │   │ LIVE MONITORING │
        └────────┬────────┘   └────────┬────────┘
                 │                     │
                 └──────────┬──────────┘
                            ▼
                  ┌───────────────────┐
                  │    RERA INSIGHT   │
                  │    APPLICATION    │
                  └───────────────────┘