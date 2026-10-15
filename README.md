# MenuPrice API

A pricing recommendation system for restaurants on UberEATS in Colombo, Sri Lanka. You give it a restaurant tier, area, cuisine, dish category and (optionally) a rating, and it recommends a selling price with competitor context.

**Demo video:** https://youtu.be/F6inQYzpEF4

*Accepted for oral presentation at NSRSIT 2026.*

## What it does

- Recommends a price for a menu item across three tiers: Budget, Mid-Range and Fine Dining
- Uses a separate model for each tier (Random Forest and XGBoost), with A/B model versioning (Version A and Version B feature sets)
- Compares the price to similar dishes in the same tier and category (competitor range, number of competitors, positioning percentile)
- Gives a confidence level (High, Medium or Low) based on how many competitors it found
- Shows a new entrant advisory when a restaurant has no rating or a very low one
- Applies price guard rails per tier, so recommendations stay in a realistic range
- Returns market insights alongside the recommendation

## Built with

Python, FastAPI, scikit-learn, XGBoost, pandas and SQLite (for logging recommendations).

## Run it locally

1. Clone the repo and open a terminal in its folder
2. Install the requirements:
```
   pip install -r requirements.txt
```
3. Start the API:
```
   uvicorn main:app --reload
```
4. Open http://localhost:8000/docs to try it in your browser

Tested with Python 3.13.

## API

| Endpoint | What it does |
|---|---|
| `GET /` | Health check |
| `GET /options` | Lists the valid tiers, areas, cuisines and dish categories |
| `POST /recommend` | Returns a price recommendation |
| `GET /logs` | Recent recommendation logs (locked, needs an admin key) |

**Example request to `/recommend`:**
```json
{
  "restaurant_tier": "Budget",
  "area": "Colombo 7",
  "cuisine_type": "Sri Lankan",
  "dish_category": "Rice & Curry",
  "restaurant_rating": 4.5
}
```

The response includes the recommended price, the competitor price range, the competitor count, the positioning percentile, the confidence level, the new entrant advisory and the market insights.

## Project structure

```
main.py            API and recommendation logic
insights.py        Market insights
models/            Trained models, label encoders and the engineered dataset
requirements.txt   Python dependencies
```

The web frontend is in a separate repo: [ubereats-pricing-ui](https://github.com/wacfernando/ubereats-pricing-ui).

## Author

Adheesha Fernando, final-year Data Science undergraduate at NSBM Green University.
[LinkedIn](https://www.linkedin.com/in/adheesha-fernando-5b8975230) · [GitHub](https://github.com/wacfernando)
