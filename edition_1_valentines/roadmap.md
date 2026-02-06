# Roadmap

## Phase 1 - Local prototype polish (1-2 days)
- Add input validation and empty-state UX across all pages.
- Add simple filters (date range, region) to Sales and Global Love pages.
- Add CSV export for each dashboard table.
- Add basic error page for missing data or invalid selections.
- Add a lightweight navigation summary on the home page.

## Phase 2 - Real AI integration (2-4 days)
- Replace template-based Love Letter with a real model call.
- Add prompt templates with guardrails for tone and safety.
- Add a feedback form to rate generated outputs.
- Add a feature flag to switch between local templates and AI.

## Phase 3 - Data and performance (2-3 days)
- Add a data refresh script for SQLite rebuilds.
- Add caching for heavy queries.
- Add indexes for frequently filtered columns.
- Add data quality checks (nulls, ranges, duplicates).

## Phase 4 - Azure-ready packaging (2-3 days)
- Add Dockerfile and .dockerignore.
- Add App Service config (or Container Apps) and startup command.
- Add environment variable support for DB and model endpoints.
- Add basic health check endpoint.

## Phase 5 - Demo and storytelling (1-2 days)
- Add a guided demo path with sample selections.
- Add screenshots and short demo script.
- Add a 4-minute pitch outline with key metrics.
