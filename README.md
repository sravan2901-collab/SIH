# SIH — LMPC Compliance System

An AI-based compliance checking system to detect Legal Metrology labelling violations on packaged commodities under the Legal Metrology (Packaged Commodities) Rules, 2011 via image capture, optical character recognition (OCR), field classification, readability analysis, and automated rule validation.

## Repository Structure

- `backend/` — FastAPI backend service for REST APIs, database models, and object storage integration.
- `frontend-web/` — React 18 web application for inspector reviews and administrative compliance dashboards.
- `frontend-mobile/` — Flutter mobile application for field inspectors with camera guidance and offline capture queue.
- `ml-pipeline/` — Celery asynchronous worker pipeline for image preprocessing, OCR, layout analysis, and rule validation.
- `infra/` — Deployment infrastructure including Docker Compose and Kubernetes Helm charts.
- `rule-configs/` — Versioned LMPC 2011 rule configurations, regex patterns, and seed data.

Status: Phase 0 — Foundation in progress