from django.core.paginator import Paginator
from django.db.models import Q
from django.db import transaction
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django import forms

from .models import RegisteredCustomer
from .forms import LoginOrRegisterForm

import logging
logger = logging.getLogger(__name__)


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


# ============================================================
# 🔹 CUSTOMER SELF-REGISTRATION
# ============================================================

def register(request):
    """
    Hybrid register/login:
      - If username+password or email+password match → log in.
      - Else create new account.
      - After successful login, ensure address info is present or prompt to add it.
    """
    from django.contrib.auth import authenticate, login
    from django.contrib.auth.models import User
    from django.db import transaction
    from django.contrib import messages
    from .forms import LoginOrRegisterForm
    from .models import RegisteredCustomer

    if request.method == "POST":
        form = LoginOrRegisterForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data["username"].strip()
            email = form.cleaned_data["email"].strip().lower()
            password1 = form.cleaned_data["password1"]

            print(f"\n=== DEBUG: register() called ===")
            print(f"username={username}, email={email}")

            # ======================================================
            # CASE 1 — Username + password match → login
            # ======================================================
            user = authenticate(request, username=username, password=password1)
            if user:
                login(request, user)
                messages.success(
                    request, f"Welcome back {user.first_name or user.username}!"
                )
                return _post_login_address_check(request, user)

            # ======================================================
            # CASE 2 — Email + password match → login
            # ======================================================
            user_by_email = User.objects.filter(email__iexact=email).first()
            if user_by_email:
                user = authenticate(
                    request, username=user_by_email.username, password=password1
                )
                if user:
                    login(request, user)
                    messages.success(
                        request, f"Welcome back {user.first_name or user.username}!"
                    )
                    return _post_login_address_check(request, user)
                else:
                    messages.error(
                        request, "Incorrect password for this email.")
                    return render(request, "customers/register.html", {"form": form})

            # ======================================================
            # CASE 3 — Username already exists but password incorrect
            # ======================================================
            existing_user = User.objects.filter(username=username).first()
            if existing_user:
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
                    street_address="",
                    city="",
                    state="",
                    zipcode="",
                    phone="",
                )

            # ✅ Authenticate before logging in to attach backend
            authenticated_user = authenticate(
                request, username=user.username, password=form.cleaned_data["password1"]
            )
            if authenticated_user:
                login(request, authenticated_user)
                messages.success(
                    request,
                    "Registration successful — please complete your profile.",
                )
                return redirect("customers:complete_profile")
            else:
                messages.warning(
                    request,
                    "Your account was created, but we couldn’t log you in automatically. Please sign in.",
                )
                return redirect("login")

        else:
            print("❌ Form invalid:", form.errors)
            messages.error(request, "Please correct the errors below.")
            return render(request, "customers/register.html", {"form": form})

    # ------------------------------------------------------
    # GET request
    # ------------------------------------------------------
    form = LoginOrRegisterForm()
    return render(request, "customers/register.html", {"form": form})


def _post_login_address_check(request, user):
    """
    After login, check if RegisteredCustomer has valid address.
    - If missing → redirect to complete_profile
    - If present → preload service/billing address in session
    """
    from django.contrib import messages
    from .models import RegisteredCustomer

    try:
        rc = RegisteredCustomer.objects.get(user=user)
        address_fields = [
            rc.street_address.strip() if rc.street_address else "",
            rc.city.strip() if rc.city else "",
            rc.state.strip() if rc.state else "",
            rc.zipcode.strip() if rc.zipcode else "",
        ]
        if not all(address_fields):
            messages.warning(
                request,
                "Your profile is missing address details. "
                "Please complete your profile before booking services."
            )
            return redirect("customers:complete_profile")

        # Store valid address in session (for search + checkout)
        full_address = f"{rc.street_address}, {rc.city}, {rc.state} {rc.zipcode}".strip(
            ", ")
        request.session["service_address"] = full_address
        request.session["billing_address"] = full_address
        request.session.modified = True
        print(f"✅ Address loaded to session: {full_address}")
        return redirect("home")

    except RegisteredCustomer.DoesNotExist:
        messages.warning(
            request,
            "No customer profile found. Please add your address to continue."
        )
        return redirect("customers:complete_profile")


# ============================================================
# 🔹 CUSTOMER PROFILE COMPLETION
# ============================================================
@login_required
def complete_profile(request):
    """
    Let users complete or update their profile (address, phone, etc.).
    If they already have a RegisteredCustomer record, update it.
    If not, create one with proper email/user linkage.
    """
    from django import forms
    from django.contrib import messages
    from django.shortcuts import redirect, render
    from .models import RegisteredCustomer

    # ✅ Always fetch or create safely
    profile, created = RegisteredCustomer.objects.get_or_create(
        user=request.user,
        defaults={
            "first_name": request.user.first_name,
            "last_name": request.user.last_name,
            "email": request.user.email,
        },
    )

    # ✅ Inline form definition
    class InlineProfileForm(forms.ModelForm):
        class Meta:
            model = RegisteredCustomer
            fields = ["street_address", "city", "state", "zipcode", "phone"]
            widgets = {
                field: forms.TextInput(attrs={"class": "form-control"})
                for field in ["street_address", "city", "state", "zipcode", "phone"]
            }

    if request.method == "POST":
        form = InlineProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                "Your profile has been saved. You can now search for available services."
            )
            return redirect("base_search")  # ✅ Goes to project-level template
    else:
        form = InlineProfileForm(instance=profile)

    return render(request, "customers/complete_profile.html", {"form": form})
