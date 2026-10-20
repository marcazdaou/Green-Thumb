# Green Thumb

A full-stack Django store for reusable and garden goods, built on **real retail data** and paired with a
data science study of **1,067,371 real transactions** from a UK online retailer.

**Live site:** https://green-thumb-1-lc2c.onrender.com (free hosting: the first visit can take ~50 seconds to wake up)

- **Data science:** cleaning pipeline, customer segmentation (RFM + k-means), a repurchase prediction model
  with out-of-time validation and bootstrap confidence intervals, cohort retention, and market basket analysis.
- **Web app:** real catalog and prices, "frequently bought together" recommendations from real orders,
  server-side pricing, reviews tied to accounts and products, **Stripe Checkout in test mode**, and an
  interactive **Insights** dashboard.
- **Engineering:** relational schema with foreign keys and constraints, signature-verified payment webhooks,
  76 automated tests, and environment-based production settings.

> **Portfolio store.** Nothing is actually sold or shipped. Payments run in Stripe *test mode* only (the code
> refuses live keys), so no real money can move. Product names, prices (GBP) and sales history are real;
> product photos show the type of product, not the exact item.

---

## Key findings

| Question | Answer |
|---|---|
| Who drives revenue? | **Champions** are 20% of customers but 73% of revenue (RFM segmentation, k = 4). |
| Do new customers come back? | On average **20%** of new customers order again the following month. |
| Can we predict who returns in the next 90 days? | Yes: gradient boosting reaches **ROC AUC 0.795** (95% CI 0.783–0.806) on a future period, vs **0.762** for a "most recent customers first" rule. A paired bootstrap puts the gain at **+0.032 (95% CI +0.026 to +0.040)**. |
| How useful is that ranking? | The top 10% of scored customers repurchased at **94%**, versus **44%** overall. |
| What predicts a return? | Days since last order and the typical gap between orders (permutation importance). |
| What is bought together? | 36,106 multi-item orders give 91,645 product pairs bought together in at least 60 orders; e.g. a garden fork and the matching trowel appear together **180×** more often than chance. |
| Do the "bought together" suggestions work? | Tested on the last 90 days of orders using rules learned only from earlier orders: with 3 suggestions, at least one was in the same order **52%** of the time vs **48%** for suggesting the 3 best-sellers, **+4.2 points (paired 95% CI +2.3 to +6.3)**. Real but modest: best-sellers are a strong baseline in a wholesale shop. |
| When does the business sell? | Revenue peaks every autumn before Christmas; only 30 of 39,251 orders were placed on a Saturday, a sign that most customers are businesses. |

One honest caveat the dashboard reports rather than hides: the model's **probabilities are too low** in the
test period (it predicted 33% on average, but 44% of customers returned), because the test window is the
holiday season. The *ranking* holds; the probabilities would need seasonal recalibration.

---

## Data

**Source:** Chen, D. (2012). *Online Retail II* [Dataset]. UCI Machine Learning Repository.
https://doi.org/10.24432/C5CG6D (CC BY 4.0). All transactions of a UK-based online retailer that sells
giftware and homeware, Dec 2009 – Dec 2011; many of its customers are wholesalers.

**Cleaning** (`analysis/data.py`), each step counted and shown on the dashboard:

| Step | Rows |
|---|---:|
| Raw transaction lines | 1,067,371 |
| Remove exact duplicates | 1,033,036 |
| Set cancellations aside (used for the 7.1% return rate) | 1,013,932 |
| Remove sales fully reversed by a later cancellation | 1,007,600 |
| Keep real products only (drop postage, fees, adjustments) | 1,002,962 |
| Keep positive quantity and price | **997,035** |
| …of which have a customer ID (used for customer analyses) | 770,398 |

Removing reversed sales matters: without it, a few orders that were placed and immediately cancelled
(for example 80,995 units of one item) dominate revenue.

---

## Methods

| Analysis | Method | Validation |
|---|---|---|
| Business metrics | Monthly revenue, orders, customers; country mix; weekday × hour pattern | Months are real dates, so they sort in time order; the final partial month is flagged |
| Cohort retention | Share of each first-purchase month that orders again k months later | Partial final month excluded; unobservable cells left blank, not 0% |
| Segmentation | Recency, frequency, spend → log + standardize → k-means | k chosen by silhouette among 3–6 (scores reported for k = 2–8); names derived from cluster medians |
| Repurchase prediction | Logistic regression and gradient boosting on 11 behavioral features | **Out-of-time:** trained on 4 snapshots (Sep 2010 – Jun 2011) whose label windows all end before the test snapshot (Sep 2011). ROC AUC with 95% bootstrap CIs; paired bootstrap vs baseline; calibration and lift by decile |
| Recommendations | Association rules (support, confidence, lift) from a sparse basket × product matrix | Minimum 150 baskets per product and 60 per pair so rules aren't driven by a few orders. **Out-of-time hit rate@K** (K = 1, 3, 5): rules from orders before Sep 10, 2011 scored on the 6,241 later orders vs a best-seller baseline, with bootstrap CIs and a paired CI for the difference (resampling orders) |
| Store catalog | The 12 most-bought items in each of 3 categories, still sold in the last quarter, at their median recent price | Rules in `analysis/catalog.py`, tested |

| Model (test period) | ROC AUC (95% CI) | PR AUC | Brier |
|---|---:|---:|---:|
| Recency rule (baseline) | 0.762 (0.749–0.776) | 0.686 | – |
| Logistic regression | 0.788 (0.776–0.801) | 0.759 | 0.190 |
| **Gradient boosting** | **0.795 (0.783–0.806)** | **0.770** | 0.194 |

---

## The web app

| Page | What it does |
|---|---|
| **Shop** | 36 real products with category filter, search and sorting (all server-side) |
| **Product** | Real sales history, "frequently bought together" from real baskets, reviews |
| **Cart** | Stores only product ids and quantities; prices and totals always come from the server |
| **Checkout** | Stripe Checkout (test mode): the order is saved as *pending*, the shopper pays on Stripe's hosted page, and the order becomes *paid* only after Stripe confirms it (return page re-checks with Stripe, plus a signature-verified webhook). Card details never reach this server. Without a Stripe key, orders are recorded with no payment step |
| **Insights** | Interactive dashboard (Plotly) of every analysis above, plus this store's own live orders and reviews |
| **Reviews** | Ratings by signed-in users; one review per user per product; only the author can delete |

**Fixes over the first version:**
- **Security:** checkout trusted the price sent by the browser. Prices now come from the database, and tampering is covered by a test.
- **Fake data:** five hard-coded reviews were mixed into the analytics. They are gone, and every number now comes from real data.
- **Chart bug:** monthly charts sorted "Apr" before "Jan". Months are grouped by real dates now.
- **Schema:** reviews and orders referenced products by free text, and prices were floats. They now use foreign keys, `Decimal` money, uniqueness and check constraints.
- **Logout:** it worked over GET, so another site could sign users out. It is POST-only now.
- **Repo:** committed build files and an unused `.env` step were removed, and the old single test is replaced by 76 tests.

---

## Run it locally

Requires Python 3.11+.

```bash
git clone https://github.com/marcazdaou/Green-Thumb.git
cd Green-Thumb/backend
python -m venv venv
venv\Scripts\activate            # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py load_catalog    # loads the real catalog + recommendations
python manage.py runserver
```

Open http://127.0.0.1:8000. Optional admin account: `python manage.py createsuperuser`, then `/admin`.

The dashboard and catalog read committed result files, so the site works without re-running the analysis.

### Turn on Stripe payments (test mode, optional)

1. Create a free account at [stripe.com](https://stripe.com) (no business details needed for test mode).
2. In the Stripe dashboard, with **Test mode** on, copy the secret key (`sk_test_...`) from *Developers → API keys*.
3. Create `backend/.env` (git-ignored) containing `STRIPE_SECRET_KEY=sk_test_...` and restart the server.
4. Check out with the test card `4242 4242 4242 4242`, any future expiry date and any CVC.

Live keys (`sk_live_...`) are rejected on purpose. To also receive Stripe's webhook, add an endpoint for
`https://<your-site>/stripe/webhook/` (event `checkout.session.completed`) and set `STRIPE_WEBHOOK_SECRET`.

### Re-run the data science pipeline (optional)

```bash
# from the repository root, with the venv active
pip install -r requirements-dev.txt
python -m analysis.run_pipeline   # downloads the dataset on first run (~45 MB), ~1.5 minutes
cd backend && python manage.py load_catalog
```

### Run the tests

```bash
# from the repository root
pytest                            # 76 tests: cleaning rules, statistics, models, pricing, payments, reviews, pages
```

---

## Deploying to Render

| Setting | Value |
|---|---|
| Root Directory | `backend` |
| Build Command | `pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate && python manage.py load_catalog` |
| Start Command | `gunicorn greenthumb.wsgi:application` |
| Environment | `SECRET_KEY` (required); optional `STRIPE_SECRET_KEY` (test key) and `STRIPE_WEBHOOK_SECRET` |

Render sets `RENDER=true`, which switches the app to production settings (debug off, secure cookies,
HTTPS redirect). Migration `0006` replaces the original demo tables, so earlier test orders and reviews are removed.

---

## Project structure

```
Green-Thumb/
├── analysis/                    Data science pipeline (pandas, scikit-learn, SciPy)
│   ├── data.py                  Download, load and clean transactions
│   ├── metrics.py               Business metrics and cohort retention
│   ├── segmentation.py          RFM + k-means customer segments
│   ├── repurchase.py            Repurchase model, bootstrap CIs, calibration
│   ├── baskets.py               Association rules ("bought together")
│   ├── catalog.py               Store catalog from real products
│   └── run_pipeline.py          Runs everything, writes the JSON files below
├── backend/
│   ├── greenthumb/              Settings (environment-based) and URLs
│   ├── store/                   Shop: models, server-side cart, views, templates
│   │   ├── cart.py              Validation and pricing for checkout
│   │   ├── payments.py          Stripe Checkout (test mode) and webhook verification
│   │   ├── data/catalog.json    Pipeline output: products + recommendations
│   │   └── management/commands/load_catalog.py
│   └── insights/                Dashboard app
│       ├── data/results.json    Pipeline output: every analysis result
│       └── static/insights/js/dashboard.js   Plotly charts
├── assets/images/               Product photos (credits in assets/images/products/CREDITS.md)
├── tests/                       pytest suite (analysis + web)
├── requirements-analysis.txt    Pipeline dependencies
└── requirements-dev.txt         Everything, including tests
```

## Author

**Marc Abi Zeid Daou** · [GitHub](https://github.com/marcazdaou)
