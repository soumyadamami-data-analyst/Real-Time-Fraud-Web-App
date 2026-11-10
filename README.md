# Fraud Transaction Lookup

A web app that gives an instant fraud assessment for a single transaction. Enter a transaction ID and the app scores it with three detection layers, then shows the verdict, a confidence gauge, and what each layer decided.

**Live demo:** _add your Streamlit Cloud link here_

## How to use it

1. Enter a transaction ID (for example `T00001234`) and press **Check Transaction**, or click one of the IDs under **Try an example** in the sidebar.
2. Read the result card:
   - **Verdict and confidence gauge**, colour-coded by risk (high, medium, low)
   - **Layer pills** showing what each detection layer decided
   - **Transaction details**: type, amount, and origin balances before and after
   - **Ground truth** from the dataset (fraud or legitimate), so you can see whether the system was right
3. Previous lookups are saved in the sidebar for the session.

> **Note:** The demo database holds **every fraud case plus a sample of the legitimate transactions** from the full PaySim dataset, to keep the app lightweight. If an ID isn't found, use the example IDs in the sidebar.

## How a transaction is scored

A transaction is flagged if **any** of the three layers fires:

| Layer | Type | Logic |
|---|---|---|
| Rule engine | Hand-written rule | `TRANSFER` or `CASH_OUT` that empties the origin account (new balance = 0, old balance > 0) with amount > 100,000 |
| Random Forest | Supervised ML | Flags the transaction if fraud probability ≥ 0.5 |
| Isolation Forest | Unsupervised anomaly detection | Flags statistically unusual transactions |

## Files

| File | Purpose |
|---|---|
| `streamlit_app.py` | The web app (UI, database lookup, scoring call) |
| `fraud_scoring.py` | The 3-layer scoring logic |
| `isolation_forest.joblib` | Trained Isolation Forest model |
| `requirements.txt` | Python dependencies |

## Run it locally

```
pip install -r requirements.txt
streamlit run streamlit_app.py
```

The app opens at http://localhost:8501. The models were trained with scikit-learn 1.8.0, which is pinned in `requirements.txt`.

## Tech stack

Python, Streamlit, scikit-learn (Random Forest, Isolation Forest), SQLite

## Dataset

[PaySim](https://www.kaggle.com/datasets/ealaxi/paysim1) synthetic mobile-money transactions. PaySim has no native transaction ID, so IDs (`T00000001`, `T00000002`, …) were assigned in row order when the database was built.

## Full project

This web app is the lookup component of a larger real-time pipeline (Kafka streaming, live dashboard, and FastAPI backend), which is not included in this repo.
