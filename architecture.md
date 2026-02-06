# Architecture Overview

This app is a small, data-driven web experience built to showcase Valentine-themed analytics and interactive features. It uses a lightweight Python web server, a built-in database, and simple web pages to deliver insights from CSV datasets.

## At-a-Glance Diagram

```
Browser
	|
	v
FastAPI web app
	|  \__ Jinja2 templates + CSS
	|
	v
SQLite database (valentines.db)
	^
	|
CSV datasets loaded on startup
```

## Technology Summary (Customer-Friendly)

- Web application: Python FastAPI serves the website and handles user requests.
- User interface: HTML templates (Jinja2) and CSS provide the pages and styling.
- Data storage: SQLite keeps all data in a local file database.
- Data ingestion: Pandas loads CSV datasets into the database on first start.
- Business logic: Python query functions calculate recommendations, dashboards, and scores.

## How It Works

1. When the app starts, it loads the CSV datasets into SQLite if they are not already there.
2. Users open the site in a browser and choose features like recommendations or dashboards.
3. Each page calls a focused query that reads the database and returns results.
4. The server renders a web page with those results and sends it back to the user.

## Core Building Blocks

- Web server: FastAPI handles routes such as /recommender, /sales-dashboard, /global-love.
- Templates: Jinja2 renders the results into human-friendly pages.
- Database: SQLite keeps data local and fast for demos and small deployments.
- Data loader: A startup step imports CSV data into tables and creates indexes.
- Queries: Dedicated functions compute metrics like compatibility scores and sales summaries.

## Why This Design

- Fast to set up: no external database or services required.
- Easy to demo: everything runs locally with one Python process.
- Clear separation: pages, data, and logic are in distinct layers.

## Typical Deployment Options

- Local demo on a laptop using Python.
- Containerized deployment for quick hosting.
- Small server or app service that can run a Python web app.

## Audience Views

### Non-Technical Executive View

This is a single, lightweight web application that turns curated datasets into interactive insights and recommendations. It is easy to demo, quick to set up, and designed to tell a data story with minimal infrastructure.

### Partner or Customer View

The experience is a simple website. Users pick a feature (recommendations, dashboards, or metrics), and the app responds instantly using the embedded data. It is built for clarity and speed rather than enterprise complexity.

### Developer View

FastAPI serves routes, Jinja2 renders HTML templates, and SQLite stores the imported CSV data. On startup, the data loader imports CSVs and creates indexes, and query functions power each page.

## Azure Hosting Options (High-Level)

- Azure App Service (Linux): Run the Python web app with minimal setup and straightforward scaling.
- Azure Container Apps: Package the app as a container for simple, serverless-style deployment.
- Azure VM: Full control for a custom runtime or learning environments.

For production needs, consider replacing local SQLite with a managed database and using object storage for larger datasets.
