"""Views for the shop: pages, the cart/checkout JSON API, reviews and accounts."""
import json
import logging
from urllib.parse import urlencode

import stripe

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.db import IntegrityError, transaction
from django.db.models import Avg, Count, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.views.decorators.http import require_POST

from insights.loader import load_results

from . import payments
from .cart import CartError, parse_items, place_order, price_cart
from .forms import ReviewForm, SignUpForm
from .models import Order, Product, Review

logger = logging.getLogger(__name__)

SORTS = {"popular": ("-historical_customers", "name"), "price_low": ("price", "name"),
         "price_high": ("-price", "name"), "name": ("name",)}


def _safe_next(request, default="home"):
    """The ?next= URL if it points to this site, otherwise the default page."""
    target = request.POST.get("next") or request.GET.get("next")
    if target and url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()},
                                                  require_https=request.is_secure()):
        return target
    return reverse(default)


# ── Pages ─────────────────────────────────────────────────────────────────────
def home_view(request):
    results = load_results()
    return render(request, "store/index.html", {
        "kpis": results["overview"]["kpis"] if results else None,
        "featured": Product.objects.all()[:4],
    })


def about_view(request):
    return render(request, "store/about.html", {"results": load_results(), "stripe_enabled": payments.enabled()})


def shop_view(request):
    """Catalog with optional category filter, text search and sort (all server-side)."""
    products = Product.objects.annotate(avg_stars=Avg("reviews__stars"), n_reviews=Count("reviews"))
    category = request.GET.get("category", "")
    query = request.GET.get("q", "").strip()
    sort = request.GET.get("sort", "popular")
    if category:
        products = products.filter(category=category)
    if query:
        products = products.filter(Q(name__icontains=query) | Q(category__icontains=query))
    products = products.order_by(*SORTS.get(sort, SORTS["popular"]))
    return render(request, "store/shop.html", {
        "products": products, "categories": Product.objects.values_list("category", flat=True)
        .distinct().order_by("category"), "category": category, "query": query, "sort": sort,
    })


def product_detail_view(request, pk):
    product = get_object_or_404(Product, pk=pk)
    reviews = product.reviews.select_related("user")
    already_reviewed = request.user.is_authenticated and reviews.filter(user=request.user).exists()
    return render(request, "store/product_detail.html", {
        "product": product,
        "recommendations": product.recommendations.select_related("recommended")[:3],
        "reviews": reviews,
        "rating": reviews.aggregate(avg=Avg("stars"), n=Count("id")),
        "form": ReviewForm(initial={"product": product}),
        "already_reviewed": already_reviewed,
    })


@ensure_csrf_cookie
def cart_view(request):
    """Empty shell; cart.js asks /api/cart/ for server-side prices and renders the lines.

    The page has no form, so ensure_csrf_cookie makes Django send the CSRF
    cookie that cart.js needs for its POST requests.
    """
    return render(request, "store/cart.html", {"stripe_enabled": payments.enabled(), "test_card": payments.TEST_CARD})


def reviews_view(request):
    reviews = Review.objects.select_related("product", "user")
    distribution = {row["stars"]: row["n"] for row in reviews.values("stars").annotate(n=Count("id"))}
    total = sum(distribution.values())
    rows = [{"stars": s, "count": distribution.get(s, 0),
             "percent": round(100 * distribution.get(s, 0) / total) if total else 0} for s in range(5, 0, -1)]
    return render(request, "store/reviews.html", {
        "reviews": reviews, "rows": rows, "total": total,
        "average": reviews.aggregate(avg=Avg("stars"))["avg"],
        "form": ReviewForm(),
    })


# ── Cart & checkout API (JSON) ────────────────────────────────────────────────
def _json_body(request):
    try:
        return json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        raise CartError("Request body must be JSON.") from None


@require_POST
def cart_api(request):
    """Price a cart: {"items": [{"id", "qty"}]} -> lines and total from the database."""
    try:
        lines, total = price_cart(parse_items(_json_body(request).get("items")))
    except CartError as e:
        return JsonResponse({"error": str(e)}, status=400)
    return JsonResponse({
        "lines": [{"id": l["product"].pk, "name": l["product"].name,
                   "image_url": l["product"].image_url,
                   "url": l["product"].get_absolute_url(), "quantity": l["quantity"],
                   "unit_price": str(l["unit_price"]), "line_total": str(l["line_total"])} for l in lines],
        "total": str(total),
    })


@require_POST
def checkout_api(request):
    """Place an order. Prices come from the database, never from the request.

    With Stripe configured, the order starts as "pending" and the response
    includes a checkout_url (Stripe's hosted payment page). Without Stripe, the
    order is simply recorded as "placed".
    """
    use_stripe = payments.enabled()
    try:
        quantities = parse_items(_json_body(request).get("items"))
        order = place_order(quantities, user=request.user,
                            status=Order.Status.PENDING if use_stripe else Order.Status.PLACED)
    except CartError as e:
        return JsonResponse({"error": str(e)}, status=400)
    data = {"order_id": order.pk, "total": str(order.total), "status": order.status}
    if use_stripe:
        try:
            data["checkout_url"] = payments.create_checkout_session(order, request)
        except stripe.StripeError:
            logger.exception("Stripe checkout session failed for order %s", order.pk)
            order.delete()   # don't leave an unpayable order behind
            return JsonResponse({"error": "The payment service is unavailable. Please try again."}, status=502)
    return JsonResponse(data, status=201)


def checkout_success_view(request):
    """Stripe sends the shopper here after paying; confirm with Stripe before showing "paid"."""
    order = None
    session_id = request.GET.get("session_id", "")
    if payments.enabled() and session_id.startswith("cs_"):
        try:
            order = payments.confirm_from_redirect(session_id)
        except stripe.StripeError:
            logger.exception("Could not confirm Stripe session %s", session_id)
    return render(request, "store/checkout_success.html", {"order": order})


@csrf_exempt     # Stripe can't send a CSRF token; the signature check below replaces it
@require_POST
def stripe_webhook(request):
    """Stripe's server-to-server payment notifications (signature-verified)."""
    try:
        payments.handle_webhook(request.body, request.headers.get("Stripe-Signature"))
    except (ValueError, stripe.SignatureVerificationError):
        return HttpResponse(status=400)
    return HttpResponse(status=200)


# ── Reviews ───────────────────────────────────────────────────────────────────
@login_required
@require_POST
def submit_review_view(request):
    form = ReviewForm(request.POST)
    if form.is_valid():
        review = form.save(commit=False)
        review.user = request.user
        try:
            # Own transaction (savepoint), so a duplicate-review error doesn't break the request's connection.
            with transaction.atomic():
                review.save()
            messages.success(request, "Thanks! Your review was posted.")
        except IntegrityError:
            messages.error(request, "You have already reviewed this product.")
    else:
        messages.error(request, "Please choose a product, a rating and write a short review.")
    return redirect(_safe_next(request, default="reviews"))


@login_required
@require_POST
def delete_review_view(request, review_id):
    """Only the author can delete their review; anyone else gets a 404."""
    review = get_object_or_404(Review, pk=review_id, user=request.user)
    review.delete()
    messages.success(request, "Your review was deleted.")
    return redirect(_safe_next(request, default="reviews"))


# ── Accounts ──────────────────────────────────────────────────────────────────
def register_view(request):
    next_url = _safe_next(request)
    form = SignUpForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Account created. Please sign in.")
        return redirect(f"{reverse('login')}?{urlencode({'next': next_url})}")
    return render(request, "store/register.html", {"form": form, "next": next_url})


def login_view(request):
    next_url = _safe_next(request)
    if request.user.is_authenticated:
        return redirect(next_url)
    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.get_user())
        return redirect(next_url)
    return render(request, "store/login.html", {"form": form, "next": next_url})


@require_POST
def logout_view(request):
    """POST only, so a link or image on another site cannot sign users out."""
    logout(request)
    return redirect(_safe_next(request))
