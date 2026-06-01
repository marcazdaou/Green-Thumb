# Green Thumb

A full-stack e-commerce web application for eco-friendly and reusable products. Built with Django, vanilla JavaScript, and pandas. Includes user authentication, a product catalog loaded from a database, customer reviews, a shopping cart, and a data analytics dashboard.

Live demo: https://green-thumb-bxmc.onrender.com
---

## Features

- Product catalog sourced from a PostgreSQL/SQLite database
- Shopping cart with localStorage persistence, scoped per user account
- Customer reviews with star ratings — stored in the database, deletable by the author
- Analytics dashboard powered by pandas: average ratings, review activity over time, revenue by product, monthly sales
- Order tracking — each checkout records items to the database for analysis
- User authentication — register, log in, log out, with session-scoped cart
- Admin panel for managing products, reviews, orders, and user accounts

---

## Tech Stack

| Layer      | Technology                          |
|------------|-------------------------------------|
| Backend    | Python 3, Django 5                  |
| Database   | SQLite (dev) / PostgreSQL (prod)    |
| Data       | pandas                              |
| Frontend   | HTML, CSS, JavaScript               |
| Charts     | Chart.js                            |
| Deployment | Render, WhiteNoise (static files)   |

---

## Prerequisites

- Python 3.10 or higher
- pip

---

## Local Setup

### 1. Clone the repository

```bash
git clone https://github.com/marcazdaou/Green-Thumb.git
```

### 2. Create and activate a virtual environment

```bash
cd backend

python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Generate a secret key:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Create a file named `.env` inside the `backend` directory with the following content, replacing the placeholder with the key you just generated:

```
SECRET_KEY=your_generated_key_here
```

### 5. Apply database migrations

```bash
python manage.py migrate
```

### 6. Seed the product catalog

```bash
python manage.py seed_products
```

### 7. Create an admin account

```bash
python manage.py createsuperuser
```

Enter a username, email, and password when prompted. This account is used to access the admin panel.

### 8. Run the development server

```bash
python manage.py runserver
```

The application will be available at http://127.0.0.1:8000/

---

## Admin Panel

Available at http://127.0.0.1:8000/admin

Log in with the superuser account created above. From here you can add, edit, or delete products, reviews, orders, and user accounts.

---

## Deploying to Render

1. Create a new Web Service on Render and connect this repository.
2. Set the following configuration:

| Setting           | Value                                                                                                   |
|-------------------|---------------------------------------------------------------------------------------------------------|
| Root Directory    | `backend`                                                                                               |
| Build Command     | `pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate && python manage.py seed_products` |
| Start Command     | `gunicorn greenthumb.wsgi:application`                                                                  |
| Environment       | Python 3                                                                                                |

3. Add the following environment variable:

| Key         | Value                          |
|-------------|--------------------------------|
| `SECRET_KEY` | A securely generated secret key (see step 4 above) |

---

## Project Structure

```
Green-Thumb/
    assets/                      Static images served by Django
    backend/
        greenthumb/              Django project settings, URL root, WSGI
        store/                   Main application
            management/
                commands/
                    seed_products.py     Populates the product catalog
            migrations/          Database schema history
            static/store/
                css/             Per-page stylesheets
                js/              Per-page JavaScript modules
            templates/store/     HTML templates
                partials/        Reusable navbar component
            admin.py             Admin panel configuration
            forms.py             User registration form
            models.py            Database models (ShopProduct, Review, OrderItem)
            urls.py              URL routing
            views.py             Page views and API endpoints
        requirements.txt         Python dependencies
        manage.py                Django management CLI
```
