# Taste Junction
A college canteen ordering system with:
- Flask web app for student/staff ordering workflows
- MySQL backend for users and orders
- Streamlit dashboard for scheduler simulation and analytics

## Features
- Student and staff login flows
- Menu ordering and payment flow
- Order history and order tracking
- Staff/admin order management
- Simulation dashboard comparing FIFO vs adaptive hybrid scheduling

## Tech Stack
- Python
- Flask
- Streamlit
- MySQL

## Project Structure
- `app.py` - Flask application entrypoint
- `database.py` - MySQL connection and schema initialization
- `streamlit_app.py` - Streamlit dashboard UI
- `snapeats_core/` - scheduling and simulation engine
- `templates/` - Flask HTML templates
- `static/` - CSS and images
- `requirements.txt` - Python dependencies

## Prerequisites
- Python 3.10+ (recommended)
- MySQL Server running locally or remotely

## 1) Clone and install dependencies
1. Clone the repository.
2. Create and activate a virtual environment.
3. Install dependencies with `pip install -r requirements.txt`.

## 2) Configure environment variables
Set these before running the app:
- `DB_HOST` (default: `localhost`)
- `DB_USER` (default: `root`)
- `DB_PASSWORD` (required)
- `DB_NAME` (default: `taste_junction`)

Example values:
- `DB_HOST=localhost`
- `DB_USER=root`
- `DB_PASSWORD=your_mysql_password`
- `DB_NAME=taste_junction`

## 3) Run Flask app
Run `python app.py`.

The app initializes database/tables automatically through `init_db()` on startup.

## 4) Run Streamlit dashboard
Run `streamlit run streamlit_app.py`.

## Default URLs
- Flask app: `http://127.0.0.1:5000`
- Streamlit app: `http://localhost:8501`

## Notes
- Do not commit secrets or passwords.
- Local database files/caches are excluded through `.gitignore`.
