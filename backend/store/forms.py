"""Forms for creating an account and writing a review.

Django forms validate user input on the server (required fields, star range,
password rules) before anything is saved to the database.
"""
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Review


class SignUpForm(UserCreationForm):
    """Django's built-in sign-up form (username + password checks) plus first and last name."""
    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=True)

    class Meta:
        model = User
        fields = ["first_name", "last_name", "username", "password1", "password2"]


class ReviewForm(forms.ModelForm):
    """A review of one product. The user comes from the session, never from the form."""
    stars = forms.TypedChoiceField(choices=[(i, i) for i in range(5, 0, -1)], coerce=int,
                                   widget=forms.RadioSelect)

    class Meta:
        model = Review
        fields = ["product", "stars", "text"]
        widgets = {"text": forms.Textarea(attrs={"rows": 4, "maxlength": 1000,
                                                 "placeholder": "What did you think of this product?"})}
        labels = {"text": "Your review"}
