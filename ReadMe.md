# FinAssist — AI Personal Financial Assistant

## What it does
Full-stack personal finance web application that tracks daily expenditures, analyzes categorical and month-over-month spending patterns, detects anomalous transactions, and forecasts future monthly spending using machine learning.

## Tech Stack
* **Backend:** Python, Flask
* **Database:** PostgreSQL (`psycopg2`)
* **Data Analysis & ML:** pandas, NumPy, scikit-learn (`LinearRegression`, Anomaly Detection)
* **Visualization:** Matplotlib (headless `Agg` backend, in-memory `BytesIO` & `base64` encoding)
* **Frontend:** HTML5, CSS3, Jinja2, Vanilla JavaScript

## Features (Current)
- **Full-Stack Flask Web Dashboard:** Interactive UI with session-based user authentication and summary cards.
- **Transaction Manager (CRUD):** Add, edit, and delete transactions with instant client-side month filtering (`YYYY-MM` vs. All Time).
- **Dynamic Monthly Category Explorer:** Time-series aggregation using `pd.Grouper(freq="MS")` and multi-index `.unstack()`, paired with a JavaScript month selector and percentage progress bars.
- **ML Spending Prediction:** Ordinary Least Squares (`LinearRegression`) model that forecasts next month's total expenditure and renders custom Matplotlib scatter and trendline plots in memory.
- **ML Anomaly Detection:** Identifies statistically unusual transactions across historical category distributions.
- **AI Financial Reports:** Generates automated spending summaries and provisional monthly budget recommendations.
- **Dual-Layer Security & Validation:** 
  - Parameterized SQL queries (`psycopg2`) and user-scoped `WHERE` clauses to prevent SQL injection and horizontal privilege escalation.
  - Client-side (`input.max`) and server-side (`date.today()`) temporal locks to block future-dated transactions from skewing ML time-series models.

## Features (Planned)
- **Partial-Month Right-Censoring Filter:** Exclude ongoing, incomplete months from regression training sets to prevent downward slope bias.
- **Natural Language Transaction Input:** Log expenses via conversational text prompts.
- **Granular Category Forecasting:** Regularized per-category expenditure predictions and seasonal trend modeling.
- **Statement Exports:** Downloadable CSV and PDF monthly financial reports.