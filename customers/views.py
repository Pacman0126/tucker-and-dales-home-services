import logging
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, get_object_or_404
from django.shortcuts import redirect
from django.contrib.auth import get_user_model


from django.core.paginator import Paginator
from django.db.models import Q
from django.db import transaction
from django.contrib.auth.forms import UserCreationForm


from django.contrib.auth.models import User

from django.contrib import messages
from django import forms

from .models import RegisteredCustomer
from .forms import LoginOrRegisterForm


logger = logging.getLogger(__name__)

User = get_user_model()


def superuser_required(user):
    return user.is_authenticated and user.is_superuser


# ============================================================
# 🔹 ADMIN CUSTOMER MANAGEMENT
# ============================================================

@user_passes_test(superuser_required)
def customer_list(request):
    query = request.GET.get("q", "").strip()
    customers = RegisteredCustomer.objects.all().order_by("last_name", "first_name")

    if query:
        customers = customers.filter(
            Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(street_address__icontains=query)
            | Q(city__icontains=query)
            | Q(email__icontains=query)
        )
        logger.info(
            f"Search performed: '{query}' -> {customers.count()} results")

    paginator = Paginator(customers, 12)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "customers/customer_list.html",
        {"customers": page_obj, "page_obj": page_obj, "query": query},
    )


@login_required
@user_passes_test(superuser_required)
def customer_detail(request, pk):
    customer = get_object_or_404(RegisteredCustomer, pk=pk)
    return render(request, "customers/customer_detail.html", {"customer": customer})


@login_required
@user_passes_test(superuser_required)
def customer_edit(request, pk):
    """
    Allow superuser to edit customer data (inline form, no external form class).
    """
    customer = get_object_or_404(RegisteredCustomer, pk=pk)

    class InlineCustomerForm(forms.ModelForm):
        class Meta:
            model = RegisteredCustomer
            fields = [
                "first_name",
                "last_name",
                "street_address",
                "city",
                "state",
                "zipcode",
                "phone",
                "email",
            ]
            widgets = {
                field: forms.TextInput(attrs={"class": "form-control"})
                for field in [
                    "first_name",
                    "last_name",
                    "street_address",
                    "city",
                    "state",
                    "zipcode",
                    "phone",
                    "email",
                ]
            }

    if request.method == "POST":
        form = InlineCustomerForm(request.POST, instance=customer)
        if form.is_valid():
            form.save()
            logger.info(f"Customer {customer.pk} updated by {request.user}")
            messages.success(request, "Customer updated successfully.")
            return redirect("customers:customer_detail", pk=customer.pk)
    else:
        form = InlineCustomerForm(instance=customer)

    return render(
        request,
        "customers/customer_form.html",
        {"form": form, "customer": customer},
    )


@login_required
@user_passes_test(superuser_required)
def customer_delete(request, pk):
    customer = get_object_or_404(RegisteredCustomer, pk=pk)
    if request.method == "POST":
        logger.warning(f"Customer {customer.pk} deleted by {request.user}")
        customer.delete()
        messages.success(request, "Customer deleted successfully.")
        return redirect("customers:customer_list")
    return render(
        request,
        "customers/customer_confirm_delete.html",
        {"customer": customer},
    )
# ----------------------------------------------------------------
# 🧩 Helper: Safe login wrapper to set backend if missing
# ----------------------------------------------------------------


def _safe_login(request, user):
    """
    Logs the user in safely, clears stale session flags,
    and merges any pre-login (anonymous) cart with the user account.
    """
    old_session_key = request.session.session_key
    login(request, user)

    # 🧹 Clear any mismatch flags
    for key in ("force_profile_update", "entered_username"):
        request.session.pop(key, None)
    request.session.modified = True

    # 🛒 Merge any anonymous cart tied to the old session
    try:
        from billing.utils import merge_session_cart
        if old_session_key:
            merge_session_cart(old_session_key, user)
    except Exception as e:
        print(f"⚠️ Cart merge failed after login: {e}")


# ============================================================
# 🔹 CUSTOMER SELF-REGISTRATION
# ============================================================
def register(request):
    """
    Hybrid register/login:
      - Username+password → login (redirect to profile update if email mismatch)
      - Email+password → login (redirect to profile update if username mismatch)
      - Username exists but bad password → error
      - Otherwise → create new user + profile
    """
    if request.method == "POST":
        form = LoginOrRegisterForm(request.POST)

        if form.is_valid():
            username = form.cleaned_data["username"].strip()
            email = form.cleaned_data["email"].strip().lower()
            password1 = form.cleaned_data["password1"]

            # ======================================================
            # CASE 1 — Username + password match → login
            # ======================================================
            user = authenticate(request, username=username, password=password1)
            if user:
                if user.email.lower() != email:
                    messages.warning(
                        request,
                        f"Your stored email is '{user.email}', but you entered '{email}'. "
                        "Please confirm or update your profile."
                    )
                    _safe_login(request, user)
                    request.session["entered_username"] = username
                    request.session["next_after_profile"] = "billing:checkout_summary"
                    return redirect("customers:complete_profile")

                _safe_login(request, user)
                return _post_login_address_check(request, user)

            # ======================================================
            # CASE 2 — Email + password match (different username)
            # ======================================================
            user_by_email = User.objects.filter(email__iexact=email).first()
            if user_by_email:
                authenticated_user = authenticate(
                    request,
                    username=user_by_email.username,
                    password=password1,
                )
                if authenticated_user:
                    if authenticated_user.username.lower() != username.lower():
                        messages.warning(
                            request,
                            f"You’re already registered as '{authenticated_user.username}', "
                            f"but you entered '{username}'. "
                            "Please verify or update your username."
                        )
                        login(request, authenticated_user)
                        request.session["entered_username"] = username
                        request.session["next_after_profile"] = "billing:checkout_summary"
                        return redirect("customers:complete_profile")

                    # ✅ Normal email-based login
                    _safe_login(request, authenticated_user)
                    return _post_login_address_check(request, authenticated_user)

                messages.error(request, "Incorrect password for this email.")
                return render(request, "customers/register.html", {"form": form})

            # ======================================================
            # CASE 3 — Username exists but password incorrect
            # ======================================================
            if User.objects.filter(username=username).exists():
                messages.error(
                    request,
                    "That username already exists, but the password entered is incorrect.",
                )
                return render(request, "customers/register.html", {"form": form})

            # ======================================================
            # CASE 4 — Create new user
            # ======================================================
            with transaction.atomic():
                user = form.save(commit=False)
                user.email = email
                user.first_name = form.cleaned_data.get(
                    "first_name", "").strip()
                user.last_name = form.cleaned_data.get("last_name", "").strip()
                user.save()

                RegisteredCustomer.objects.create(
                    user=user,
                    first_name=user.first_name,
                    last_name=user.last_name,
                    email=user.email,
                )

            messages.success(
                request,
                "Registration successful — please complete your profile."
            )
            _safe_login(request, user)
            request.session["next_after_profile"] = "billing:checkout_summary"
            return redirect("customers:complete_profile")

        # Invalid form
        messages.error(request, "Please correct the errors below.")
        return render(request, "customers/register.html", {"form": form})

    # GET
    form = LoginOrRegisterForm()
    return render(request, "customers/register.html", {"form": form})


def _post_login_address_check(request, user):
    """
    Ensures the user’s billing address is valid.
    - Missing → redirect to complete_profile
    - Valid → preload into session and redirect home
    """
    try:
        rc = RegisteredCustomer.objects.get(user=user)

        # ✅ Ensure valid billing info
        if not rc.has_valid_billing_address():
            messages.warning(
                request,
                "Your profile is missing billing address details. "
                "Please complete your profile before checkout."
            )
            return redirect("customers:complete_profile")

        # ✅ Store billing + default service address in session
        billing_full = rc.full_billing_address
        request.session["billing_address"] = billing_full
        request.session.setdefault("service_address", billing_full)
        request.session.modified = True

        messages.success(
            request,
            f"Welcome back {user.first_name or user.username}! "
            "Your billing address has been verified."
        )
        return redirect("home")

    except RegisteredCustomer.DoesNotExist:
        messages.warning(
            request,
            "No customer profile found. Please complete your profile before checkout."
        )
        return redirect("customers:complete_profile")


# ============================================================
# 🔹 CUSTOMER PROFILE COMPLETION
# ============================================================
@login_required
def complete_profile(request):
    """
    Lets users verify or update their stored profile and billing address.
    - Shows both entered and stored username (if mismatch detected)
    - Allows any field to be freely updated
    - Displays explicit field errors instead of silent loops
    - Clears mismatch session flags after save
    """

    user = request.user
    entered_username = request.session.get("entered_username", "")

    # ✅ Inline form for RegisteredCustomer with relaxed validation
    class InlineProfileForm(forms.ModelForm):
        username = forms.CharField(
            required=False,
            label="Stored Username (you can update this)",
            widget=forms.TextInput(attrs={"class": "form-control"})
        )
        entered_username_display = forms.CharField(
            required=False,
            label="Entered Username (from login)",
            widget=forms.TextInput(
                attrs={"class": "form-control", "readonly": "readonly"}
            )
        )

        class Meta:
            model = RegisteredCustomer
            fields = [
                "first_name",
                "last_name",
                "email",
                "phone",
                "billing_street_address",
                "billing_city",
                "billing_state",
                "billing_zipcode",
            ]
            widgets = {
                "first_name": forms.TextInput(attrs={"class": "form-control"}),
                "last_name": forms.TextInput(attrs={"class": "form-control"}),
                "email": forms.EmailInput(attrs={"class": "form-control"}),
                "phone": forms.TextInput(attrs={"class": "form-control"}),
                "billing_street_address": forms.TextInput(attrs={"class": "form-control"}),
                "billing_city": forms.TextInput(attrs={"class": "form-control"}),
                "billing_state": forms.TextInput(attrs={"class": "form-control"}),
                "billing_zipcode": forms.TextInput(attrs={"class": "form-control"}),
            }

        def clean_email(self):
            """Allow free updates — only validate email format."""
            email = self.cleaned_data.get("email", "").strip().lower()
            return email

    # ✅ Get or create associated customer record
    rc, _ = RegisteredCustomer.objects.get_or_create(user=user)

    # ✅ Prepopulate both username fields
    initial = {
        "username": user.username,
        "entered_username_display": entered_username,
    }

    if request.method == "POST":
        form = InlineProfileForm(request.POST, instance=rc, initial=initial)
        if form.is_valid():
            # --- Save profile changes ---
            rc = form.save(commit=False)
            rc.save()

            # --- Update user core fields if changed ---
            new_username = form.cleaned_data.get("username", "").strip()
            if new_username and new_username != user.username:
                user.username = new_username

            new_email = form.cleaned_data.get("email", "").strip().lower()
            if new_email and new_email != user.email.lower():
                user.email = new_email

            user.first_name = rc.first_name
            user.last_name = rc.last_name
            user.save()

            # --- Clear mismatch session flags ---
            request.session.pop("entered_username", None)
            request.session.pop("force_profile_update", None)

            # --- Smart redirect based on context ---
            next_url = request.session.pop("next_after_profile", None)

            messages.success(request, "✅ Profile updated successfully!")

            if next_url:
                return redirect(next_url)
            elif "checkout" in request.META.get("HTTP_REFERER", ""):
                return redirect("billing:checkout_summary")
            else:
                return redirect("home")

        else:
            messages.error(
                request, "Please correct the highlighted errors below.")
    else:
        form = InlineProfileForm(instance=rc, initial=initial)

    return render(request, "customers/complete_profile.html", {"form": form})
