"""
views.py
Django view functions for every page and API endpoint in the store app.

Page views render an HTML template and pass data from the database as
template context.

API views accept POST requests from JavaScript and return JSON responses.
"""

from urllib.parse import urlencode

from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from .forms import SignUpForm
from .models import ShopProduct, Review, OrderItem
import json
from django.core.serializers.json import DjangoJSONEncoder
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _get_redirect_target(request, default_name='home'):
    """
    Returns a safe redirect URL after login/logout.
    Checks the POST and GET 'next' parameters first, then falls back to
    the named URL so we never send users to an external site.
    """
    redirect_to = request.POST.get('next') or request.GET.get('next')

    if redirect_to and url_has_allowed_host_and_scheme(
        redirect_to,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect_to

    return reverse(default_name)


# ---------------------------------------------------------------------------
# Page views
# ---------------------------------------------------------------------------

def home_view(request):
    """Renders the home page (hero section + feature cards). No database queries."""
    return render(request, 'store/index.html')


def shop_view(request):
    """
    Renders the shop page.
    Passes all ShopProduct rows to the template as a JSON string so the
    shop.js can combine them with the hardcoded product list and build cards.
    """
    shop_items = ShopProduct.objects.all().values()
    js_items   = json.dumps(list(shop_items), cls=DjangoJSONEncoder)
    return render(request, 'store/shop.html', {'shop_data': js_items})


def reviews_view(request):
    """
    Renders the reviews page.
    Passes all database reviews as JSON for the reviews.js to render.
    Also passes the logged-in user's ID and username so the frontend can
    show a delete button only on the user's own reviews.
    """
    reviews = list(Review.objects.order_by('-created_at').values(
        'id', 'user_id', 'name', 'product', 'stars', 'text', 'created_at'
    ))
    # Format the datetime as a human-readable month string before serialising.
    for r in reviews:
        r['date'] = r['created_at'].strftime('%b %Y')
        del r['created_at']

    context = {
        'reviews_json':      json.dumps(reviews, cls=DjangoJSONEncoder),
        'current_user_id':   request.user.id if request.user.is_authenticated else None,
        'username':          request.user.username if request.user.is_authenticated else '',
        'user_authenticated': request.user.is_authenticated,
    }
    return render(request, 'store/reviews.html', context)


def about_view(request):
    """Renders the About page. No database queries."""
    return render(request, 'store/about.html')


def cart_view(request):
    """
    Renders the cart page.
    The cart itself is stored in localStorage on the client — this view only
    delivers the empty shell that cart.js populates.
    """
    return render(request, 'store/cart.html')


# Hardcoded seed reviews that appear on the reviews page via JavaScript but
# are NOT stored in the database.  We include them here so the analytics
# dashboard counts them alongside real submitted reviews.
BASE_REVIEWS = [
    {'product': 'Cotton Tote Bag',       'stars': 4, 'created_at': None},
    {'product': 'Reusable Water Bottle', 'stars': 5, 'created_at': None},
    {'product': 'Succulents',            'stars': 5, 'created_at': None},
    {'product': 'Steel Straw Set',       'stars': 5, 'created_at': None},
    {'product': 'Flower Seeds',          'stars': 5, 'created_at': None},
]


def analytics_view(request):
    """
    Renders the analytics dashboard.

    Uses pandas to aggregate three data sources:
      1. Reviews (DB rows + BASE_REVIEWS) — ratings and distribution
      2. ShopProduct table              — catalog and price stats
      3. OrderItem table                — revenue and units sold

    All computed data is passed to the template as JSON so Chart.js can
    render the charts without any additional API calls.
    """
    import pandas as pd

    db_reviews  = list(Review.objects.values('product', 'stars', 'created_at'))
    reviews_qs  = db_reviews + BASE_REVIEWS   # merge DB reviews with hardcoded seed reviews
    products_qs = list(ShopProduct.objects.values('product_name', 'price'))
    orders_qs   = list(OrderItem.objects.values('product_name', 'quantity', 'total', 'purchased_at'))

    # ── Review analytics ──────────────────────────────────────────────────────
    if reviews_qs:
        df = pd.DataFrame(reviews_qs)

        # Average rating and review count grouped by product name.
        product_stats = df.groupby('product').agg(
            avg_rating=('stars', 'mean'),
            count=('stars', 'count')
        ).reset_index()
        product_stats['avg_rating'] = product_stats['avg_rating'].round(1)
        product_stats = product_stats.sort_values('count', ascending=False)

        # Monthly review activity — only DB reviews have timestamps.
        df_timed = pd.DataFrame(db_reviews) if db_reviews else pd.DataFrame(
            columns=['product', 'stars', 'created_at']
        )
        if not df_timed.empty and df_timed['created_at'].notna().any():
            df_timed['month'] = df_timed['created_at'].apply(
                lambda x: x.strftime('%b %Y') if x else None
            )
            monthly      = df_timed.dropna(subset=['month']).groupby('month').size().reset_index(name='count')
            monthly_data = monthly.to_dict('records')
        else:
            monthly_data = []

        # Count of each star rating (1–5) across all reviews.
        rating_counts    = df['stars'].value_counts().sort_index()
        rating_dist_data = [
            {'stars': int(s), 'count': int(c)}
            for s, c in rating_counts.items()
        ]

        total_reviews        = len(df)
        avg_rating           = round(float(df['stars'].mean()), 1)
        product_ratings_data = product_stats.to_dict('records')
    else:
        product_ratings_data = []
        monthly_data         = []
        rating_dist_data     = []
        total_reviews        = 0
        avg_rating           = 0

    # ── Product analytics ─────────────────────────────────────────────────────
    if products_qs:
        df_p           = pd.DataFrame(products_qs)
        total_products = len(df_p)
        avg_price      = round(float(df_p['price'].mean()), 2)
        price_data     = df_p.sort_values('price', ascending=False).to_dict('records')
    else:
        total_products = 0
        avg_price      = 0.0
        price_data     = []

    # ── Order / revenue analytics ─────────────────────────────────────────────
    if orders_qs:
        df_o = pd.DataFrame(orders_qs)
        df_o['purchased_at'] = pd.to_datetime(df_o['purchased_at'], utc=True)
        df_o['month']        = df_o['purchased_at'].dt.strftime('%b %Y')

        # Total revenue and units sold per product.
        revenue_by_product = df_o.groupby('product_name').agg(
            revenue=('total',    'sum'),
            units=  ('quantity', 'sum')
        ).reset_index().sort_values('revenue', ascending=False)
        revenue_by_product['revenue'] = revenue_by_product['revenue'].round(2)

        # Monthly revenue totals for the line chart.
        revenue_over_time = df_o.groupby('month')['total'].sum().reset_index(name='revenue')
        revenue_over_time['revenue'] = revenue_over_time['revenue'].round(2)

        total_revenue        = round(float(df_o['total'].sum()), 2)
        total_orders         = int(df_o['quantity'].sum())
        revenue_by_product_d = revenue_by_product.to_dict('records')
        revenue_over_time_d  = revenue_over_time.to_dict('records')
    else:
        total_revenue        = 0.0
        total_orders         = 0
        revenue_by_product_d = []
        revenue_over_time_d  = []

    context = {
        # Review data
        'product_ratings_json': json.dumps(product_ratings_data),
        'monthly_reviews_json': json.dumps(monthly_data),
        'rating_dist_json':     json.dumps(rating_dist_data),
        # Product data
        'price_data_json':      json.dumps(price_data),
        # Order / revenue data
        'revenue_by_product_json': json.dumps(revenue_by_product_d),
        'revenue_over_time_json':  json.dumps(revenue_over_time_d),
        # Summary metrics for the top cards
        'total_reviews':  total_reviews,
        'total_products': total_products,
        'avg_rating':     avg_rating,
        'avg_price':      avg_price,
        'total_revenue':  total_revenue,
        'total_orders':   total_orders,
    }
    return render(request, 'store/analytics.html', context)


# ---------------------------------------------------------------------------
# Review API endpoints
# ---------------------------------------------------------------------------

@login_required
@require_POST
def delete_review_view(request, review_id):
    """
    Deletes a review by ID.
    Only the user who wrote the review can delete it.
    Returns JSON so the frontend can update the UI without a page reload.
    """
    try:
        review = Review.objects.get(id=review_id)
        if review.user != request.user:
            return JsonResponse({'error': 'Not authorized'}, status=403)
        review.delete()
        return JsonResponse({'success': True})
    except Review.DoesNotExist:
        return JsonResponse({'error': 'Not found'}, status=404)


@login_required
@require_POST
def submit_review_view(request):
    """
    Creates a new Review row from a JSON POST body.
    Validates that all required fields are present and the star rating is 1–5.
    Returns the saved review as JSON so the frontend can prepend it to the list.
    """
    try:
        data    = json.loads(request.body)
        name    = data.get('name', '').strip()
        product = data.get('product', '').strip()
        stars   = int(data.get('stars', 0))
        text    = data.get('text', '').strip()

        if not name or not product or not text or not (1 <= stars <= 5):
            return JsonResponse({'error': 'Invalid data'}, status=400)

        review = Review.objects.create(
            user=request.user, name=name, product=product, stars=stars, text=text
        )
        return JsonResponse({
            'success': True,
            'review': {
                'id':      review.id,
                'user_id': review.user.id,
                'name':    review.name,
                'product': review.product,
                'stars':   review.stars,
                'text':    review.text,
                'date':    review.created_at.strftime('%b %Y'),
            }
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


# ---------------------------------------------------------------------------
# Order API endpoint
# ---------------------------------------------------------------------------

@require_POST
def submit_order_view(request):
    """
    Records each item in a completed cart as an OrderItem row.

    Called by cart.js when the customer clicks 'Place Order'.
    Accepts a JSON body: { items: [{ name, price, qty }, ...] }
    Allows anonymous orders (user field is nullable).
    """
    try:
        data  = json.loads(request.body)
        items = data.get('items', [])
        for item in items:
            qty   = int(item.get('qty', 1))
            price = float(item.get('price', 0))
            OrderItem.objects.create(
                product_name=item.get('name', ''),
                unit_price=price,
                quantity=qty,
                total=round(price * qty, 2),
                user=request.user if request.user.is_authenticated else None,
            )
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


# ---------------------------------------------------------------------------
# Authentication views
# ---------------------------------------------------------------------------

def register_view(request):
    """
    GET  — renders the registration form.
    POST — validates and saves the new user, then redirects to the login page
           preserving the 'next' URL so the user ends up where they intended.
    """
    next_url = _get_redirect_target(request)

    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            form.save()
            login_url    = reverse('login')
            query_string = urlencode({'next': next_url}) if next_url else ''
            return redirect(f'{login_url}?{query_string}' if query_string else login_url)
    else:
        form = SignUpForm()

    return render(request, 'store/register.html', {'form': form, 'next': next_url})


def login_view(request):
    """
    GET  — renders the login form (redirects if already authenticated).
    POST — authenticates the user and starts a session, then redirects to 'next'.
    """
    next_url = _get_redirect_target(request)

    if request.user.is_authenticated:
        return redirect(next_url)

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = authenticate(
                request,
                username=form.cleaned_data.get('username'),
                password=form.cleaned_data.get('password'),
            )
            if user is not None:
                login(request, user)
                return redirect(next_url)
    else:
        form = AuthenticationForm()

    return render(request, 'store/login.html', {'form': form, 'next': next_url})


def logout_view(request):
    """Ends the user's session and redirects back to the page they were on."""
    logout(request)
    return redirect(_get_redirect_target(request))
