"""Reviews (linked to products and users) and account flows."""
from django.contrib.auth.models import User

from store.models import Review


def test_review_requires_sign_in(client, products):
    response = client.post("/reviews/submit/", {"product": products["bag"].pk, "stars": 5, "text": "Great"})
    assert response.status_code == 302 and "/login/" in response.url
    assert Review.objects.count() == 0


def test_signed_in_user_can_review_a_product_once(signed_in, user, products):
    data = {"product": products["bag"].pk, "stars": 4, "text": "Sturdy bag."}
    signed_in.post("/reviews/submit/", data)
    signed_in.post("/reviews/submit/", data)                    # second attempt for the same product
    reviews = Review.objects.filter(user=user)
    assert reviews.count() == 1
    assert reviews.get().product == products["bag"]


def test_star_rating_must_be_1_to_5(signed_in, products):
    signed_in.post("/reviews/submit/", {"product": products["bag"].pk, "stars": 9, "text": "Hmm"})
    assert Review.objects.count() == 0


def test_only_the_author_can_delete_a_review(client, signed_in, user, products):
    review = Review.objects.create(product=products["bag"], user=user, stars=5, text="Mine")
    other = User.objects.create_user("someone", password="AnotherPass123!")
    client.force_login(other)
    assert client.post(f"/reviews/{review.pk}/delete/").status_code == 404
    assert Review.objects.filter(pk=review.pk).exists()
    client.force_login(user)
    client.post(f"/reviews/{review.pk}/delete/")
    assert not Review.objects.filter(pk=review.pk).exists()


def test_register_saves_names_and_redirects_to_login(client, db):
    response = client.post("/register/", {"first_name": "Abc", "last_name": "Gardener", "username": "abcgardener",
                                           "password1": "GardenPass123!", "password2": "GardenPass123!"})
    assert response.status_code == 302 and response.url.startswith("/login/")
    user = User.objects.get(username="abcgardener")
    assert (user.first_name, user.last_name) == ("Abc", "Gardener")


def test_login_ignores_external_next_url(client, user):
    response = client.post("/login/?next=https://evil.example.com/",
                           {"username": "gardener", "password": "GardenPass123!"})
    assert response.status_code == 302 and response.url == "/"


def test_logout_requires_post(signed_in):
    assert signed_in.get("/logout/").status_code == 405
    assert signed_in.post("/logout/").status_code == 302
