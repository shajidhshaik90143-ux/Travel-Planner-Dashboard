# Travel Planner Dashboard

A strong, production-style Streamlit travel planning dashboard.

## Features
- Trip creation and trip selector
- Destination, dates, travelers, trip type, status
- Day-by-day itinerary planner
- Activity time, category, location, cost, notes
- Budget planning and category breakdown
- Expense tracking with paid/unpaid status
- Packing checklist with progress
- Travel documents checklist
- Trip analytics and charts
- Weather notes / travel tips
- Search and filter itinerary items
- CSV and Excel exports
- Printable PDF trip summary
- SQLite persistence
- Responsive dark/light-friendly UI

## Run

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
streamlit run app.py
```

The SQLite database is created automatically in `data/travel_planner.db`.

## Project structure

```text
Travel Planner Dashboard/
├── app.py
├── requirements.txt
├── README.md
├── data/
│   └── travel_planner.db   # generated automatically
├── assets/
└── src/
    ├── __init__.py
    ├── database.py
    ├── exports.py
    └── ui.py
```
