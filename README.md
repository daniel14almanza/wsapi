
# FastAPI Screening API

Backend API that performs web scraping and screening of entities against high-risk lists (OFAC, Offshore Leaks, World Bank debarred firms). Returns structured results (hits count + result array) suitable for automatic processing or UI display.

---

## Prerequisites

- Python 3.11+
- venv (virtual environments)
- Optional: Postman

---

## Setup

1. Clone the repository:

    git clone https://github.com/username/fastapi-screening.git
    cd fastapi-screening

2. Create and activate a virtual environment:

    # Windows
    python -m venv venv
    venv\Scripts\activate

    # Linux / macOS
    python3 -m venv venv
    source venv/bin/activate

3. Install dependencies:

    pip install -r requirements.txt

---

## Run the API (development)

    uvicorn main:app --reload

- Default host/port: http://127.0.0.1:8000
- Swagger UI: http://127.0.0.1:8000/docs
- Redoc: http://127.0.0.1:8000/redoc

---

## Endpoints / Behavior (summary)

- `POST /search` – Request body includes `name` and `sources` (array of sources to query).
  - Response:
    - `hits`: integer
    - `results`: array of objects
- Authentication required
- Rate limiting: 20 calls/min

---

## Project Structure

/fastapi-screening
    app/
        main.py
        routes/
        models/
        services/
    requirements.txt
    .gitignore
    README.md
