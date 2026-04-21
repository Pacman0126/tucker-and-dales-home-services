import logging

from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_backends, login
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from billing.utils import merge_session_cart
from customers.models import CustomerProfile
from core.decorators import verified_email_required

logger = logging.getLogger(__name__)
User = get_user_model()


def superuser_required(user):
    return user.is_authenticated and user.is_superuser


@login_required
@verified_email_required
def profile_view(request):
    """
    Logged-in user's profile page.
    Loads safely even if the related profile does not exist yet.
    """
    customer_profile = CustomerProfile.objects.filter(
        user=request.user
    ).first()

    context = {
        "customer_profile": customer_profile,
        "customer": customer_profile,  # backward-compatible template alias
    }
    return render(request, "customers/profile.html", context)


# ============================================================
# 🔹 ADMIN CUSTOMER MANAGEMENT
# ============================================================
@user_passes_test(superuser_required)
def customer_list(request):
    query = request.GET.get("q", "").strip()

    customers = CustomerProfile.objects.select_related("user").all().order_by(
        "user__last_name",
        "user__first_name",
        "user__username",
    )

    if query:
        customers = customers.filter(
            Q(user__first_name__icontains=query)
            | Q(user__last_name__icontains=query)
            | Q(user__username__icontains=query)
            | Q(email__icontains=query)
            | Q(phone__icontains=query)
            | Q(company__icontains=query)
            | Q(billing_street_address__icontains=query)
            | Q(billing_city__icontains=query)
            | Q(billing_state__icontains=query)
            | Q(billing_zipcode__icontains=query)
            | Q(service_street_address__icontains=query)
            | Q(service_city__icontains=query)
            | Q(service_state__icontains=query)
            | Q(service_zipcode__icontains=query)
        )

    paginator = Paginator(customers, 12)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "customers/customer_list.html",
        {
            "customers": page_obj,
            "page_obj": page_obj,
            "query": query,
        },
    )


@login_required
@user_passes_test(superuser_required)
def customer_detail(request, pk):
    customer = get_object_or_404(
        CustomerProfile.objects.select_related("user"),
        pk=pk,
    )
    return render(
        request,
        "customers/customer_detail.html",
        {"customer": customer},
    )


@login_required
@user_passes_test(superuser_required)
def customer_edit(request, pk):
    """
    Allow superuser to edit customer User + CustomerProfile data together.
    """
    customer = get_object_or_404(
        CustomerProfile.objects.select_related("user"),
        pk=pk,
    )
    user = customer.user

    class InlineCustomerForm(forms.ModelForm):
        first_name = forms.CharField(
            required=False,
            widget=forms.TextInput(attrs={"class": "form-control"}),
        )
        last_name = forms.CharField(
            required=False,
            widget=forms.TextInput(attrs={"class": "form-control"}),
        )
        username = forms.CharField(
            required=True,
            widget=forms.TextInput(attrs={"class": "form-control"}),
        )

        class Meta:
            model = CustomerProfile
            fields = [
                "username",
                "first_name",
                "last_name",
                "email",
                "phone",
                "company",
                "preferred_contact",
                "timezone",
                "billing_street_address",
                "billing_city",
                "billing_state",
                "billing_zipcode",
                "region",
                "service_street_address",
                "service_city",
                "service_state",
                "service_zipcode",
                "service_region",
            ]
            widgets = {
                "email": forms.EmailInput(attrs={"class": "form-control"}),
                "phone": forms.TextInput(attrs={"class": "form-control"}),
                "company": forms.TextInput(attrs={"class": "form-control"}),
                "preferred_contact": forms.Select(
                    attrs={"class": "form-select"}
                ),
                "timezone": forms.TextInput(attrs={"class": "form-control"}),
                "billing_street_address": forms.TextInput(
                    attrs={"class": "form-control"}
                ),
                "billing_city": forms.TextInput(
                    attrs={"class": "form-control"}
                ),
                "billing_state": forms.TextInput(
                    attrs={"class": "form-control"}
                ),
                "billing_zipcode": forms.TextInput(
                    attrs={"class": "form-control"}
                ),
                "region": forms.TextInput(attrs={"class": "form-control"}),
                "service_street_address": forms.TextInput(
                    attrs={"class": "form-control"}
                ),
                "service_city": forms.TextInput(
                    attrs={"class": "form-control"}
                ),
                "service_state": forms.TextInput(
                    attrs={"class": "form-control"}
                ),
                "service_zipcode": forms.TextInput(
                    attrs={"class": "form-control"}
                ),
                "service_region": forms.TextInput(
                    attrs={"class": "form-control"}
                ),
            }

        def clean_email(self):
            return self.cleaned_data.get("email", "").strip().lower()

    if request.method == "POST":
        form = InlineCustomerForm(request.POST, instance=customer)
        if form.is_valid():
            updated_customer = form.save(commit=False)

            user.username = form.cleaned_data["username"].strip()
            user.first_name = form.cleaned_data.get("first_name", "").strip()
            user.last_name = form.cleaned_data.get("last_name", "").strip()
            user.email = form.cleaned_data.get("email", "").strip().lower()
            user.save()

            updated_customer.email = user.email
            updated_customer.save()

            logger.info("Customer %s updated by %s", customer.pk, request.user)
            messages.success(request, "Customer updated successfully.")
            return redirect("customers:customer_detail", pk=customer.pk)
    else:
        form = InlineCustomerForm(
            instance=customer,
            initial={
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
            },
        )

    return render(
        request,
        "customers/customer_form.html",
        {"form": form, "customer": customer},
    )


@login_required
@user_passes_test(superuser_required)
def customer_delete(request, pk):
    customer = get_object_or_404(CustomerProfile, pk=pk)

    if request.method == "POST":
        logger.warning("Customer %s deleted by %s", customer.pk, request.user)
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
    Logs in the user safely, merging any session carts.
    Supports multiple authentication backends.
    """
    old_session_key = request.session.session_key
    user._request = request  # transient ref

    if not hasattr(user, "backend"):
        backends = get_backends()
        if backends:
            user.backend = (
                f"{backends[0].__module__}.{backends[0].__class__.__name__}"
            )
        else:
            default_backend = getattr(
                settings,
                "AUTHENTICATION_BACKENDS",
                ["django.contrib.auth.backends.ModelBackend"],
            )[0]
            user.backend = default_backend

    login(request, user, backend=user.backend)

    for key in ("force_profile_update", "entered_username"):
        request.session.pop(key, None)

    try:
        merged = merge_session_cart(
            old_session_key,
            user,
        ) if old_session_key else None
        if merged:
            request.session["cart_id"] = merged.pk
        else:
            from billing.models import Cart
            cart = Cart.objects.filter(
                user=user).order_by("-updated_at").first()
            if cart:
                request.session["cart_id"] = cart.pk
        request.session.modified = True

        if request.session.get("cart_id"):
            print(
                f"🛒 Linked cart id {request.session['cart_id']} "
                f"for user '{user.username}'"
            )

    except Exception as e:
        print(f"⚠️ Cart merge/link failed: {e}")

    if hasattr(user, "_request"):
        delattr(user, "_request")


def register(request):
    """
    Legacy compatibility wrapper.
    Redirect any old register entry points to allauth signup.
    """
    next_url = request.GET.get("next") or request.POST.get("next")
    target = reverse("account_signup")
    if next_url:
        return redirect(f"{target}?next={next_url}")
    return redirect(target)


def _post_login_address_check(request, user):
    """
    Ensure user has a valid billing address; preload billing
    address to session.
    Do NOT overwrite service_address if user started a booking as a guest.
    """
    try:
        rc = CustomerProfile.objects.get(user=user)

        if not rc.has_valid_billing_address():
            messages.warning(
                request,
                (
                    "Your profile is missing billing address details. "
                    "Please complete your profile before checkout."
                )
            )
            request.session["next_after_profile"] = "billing:checkout"
            request.session["checkout_pending"] = True
            request.session.modified = True
            return redirect("customers:complete_profile")

        request.session["billing_address"] = rc.full_billing_address
        if not request.session.get("service_address"):
            request.session["service_address"] = rc.full_billing_address
        request.session.modified = True

        return redirect("core:home")
    except CustomerProfile.DoesNotExist:
        messages.warning(
            request,
            (
                "No customer profile found. "
                "Please complete your profile before checkout."
            )
        )
        request.session["next_after_profile"] = "billing:checkout"
        request.session["checkout_pending"] = True
        request.session.modified = True
        return redirect("customers:complete_profile")


# ============================================================
# 🔹 CUSTOMER PROFILE COMPLETION
# ============================================================
@login_required()
def complete_profile(request):
    """
    Lets users verify or update their stored profile and billing address.
    Redirects correctly back to checkout if triggered by checkout flow.
    """

    user = request.user
    entered_username = request.session.get("entered_username", "")
    placeholder_phone = "000-000-0000"

    class InlineProfileForm(forms.ModelForm):
        username = forms.CharField(
            required=False,
            label="Stored Username (you can update this)",
            widget=forms.TextInput(attrs={"class": "form-control"}),
        )
        entered_username_display = forms.CharField(
            required=False,
            label="Entered Username (from login)",
            widget=forms.TextInput(
                attrs={"class": "form-control", "readonly": "readonly"}
            ),
        )
        first_name = forms.CharField(
            required=False,
            label="First name",
            widget=forms.TextInput(attrs={"class": "form-control"}),
        )
        last_name = forms.CharField(
            required=False,
            label="Last name",
            widget=forms.TextInput(attrs={"class": "form-control"}),
        )

        class Meta:
            model = CustomerProfile
            fields = [
                "username",
                "entered_username_display",
                "first_name",
                "last_name",
                "email",
                "phone",
                "company",
                "preferred_contact",
                "timezone",
                "billing_street_address",
                "billing_city",
                "billing_state",
                "billing_zipcode",
                "region",
            ]
            widgets = {
                "email": forms.EmailInput(attrs={"class": "form-control"}),
                "phone": forms.TextInput(attrs={"class": "form-control"}),
                "company": forms.TextInput(attrs={"class": "form-control"}),
                "preferred_contact": forms.Select(
                    attrs={"class": "form-select"}
                ),
                "timezone": forms.TextInput(attrs={"class": "form-control"}),
                "billing_street_address": forms.TextInput(
                    attrs={"class": "form-control"}
                ),
                "billing_city": forms.TextInput(
                    attrs={"class": "form-control"}
                ),
                "billing_state": forms.TextInput(
                    attrs={"class": "form-control"}
                ),
                "billing_zipcode": forms.TextInput(
                    attrs={"class": "form-control"}
                ),
                "region": forms.TextInput(attrs={"class": "form-control"}),
            }

        def clean_email(self):
            return self.cleaned_data.get("email", "").strip().lower()

        def clean_phone(self):
            phone = self.cleaned_data.get("phone", "").strip()
            if not phone or phone == placeholder_phone:
                raise forms.ValidationError(
                    "Please enter a valid phone number so staff can contact you."
                )
            return phone

    rc, created = CustomerProfile.objects.get_or_create(
        user=user,
        defaults={
            "email": (user.email or "").strip().lower(),
            "phone": placeholder_phone,
            "preferred_contact": "email",
            "timezone": "America/Chicago",
            "region": "US",
        },
    )

    initial = {
        "username": user.username,
        "entered_username_display": entered_username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": rc.email or user.email or "",
        "phone": "" if rc.phone == placeholder_phone else rc.phone,
        "preferred_contact": rc.preferred_contact or "email",
        "timezone": rc.timezone or "America/Chicago",
        "region": rc.region or "US",
    }

    show_identity_warning = bool(
        entered_username
        and entered_username.strip().lower() != user.username.strip().lower()
    )

    if created or rc.phone == placeholder_phone:
        messages.warning(
            request,
            "Please enter a valid phone number so staff can contact you "
            "about scheduled services."
        )

    if request.method == "POST":
        form = InlineProfileForm(request.POST, instance=rc, initial=initial)
        if form.is_valid():
            rc = form.save(commit=False)

            new_username = form.cleaned_data.get("username", "").strip()
            if new_username and new_username != user.username:
                user.username = new_username

            new_email = form.cleaned_data.get("email", "").strip().lower()
            current_user_email = (user.email or "").strip().lower()
            if new_email and new_email != current_user_email:
                user.email = new_email

            user.first_name = form.cleaned_data.get("first_name", "").strip()
            user.last_name = form.cleaned_data.get("last_name", "").strip()
            user.save()

            rc.email = user.email
            rc.save()

            for key in ("entered_username", "force_profile_update"):
                request.session.pop(key, None)

            next_url = request.session.pop("next_after_profile", None)
            if not next_url and request.GET.get("next"):
                next_url = request.GET.get("next")

            if not next_url:
                if request.session.get("checkout_pending"):
                    request.session.pop("checkout_pending", None)
                    next_url = reverse("billing:checkout")
                elif "checkout" in request.META.get("HTTP_REFERER", ""):
                    next_url = reverse("billing:checkout")
                else:
                    next_url = reverse("core:home")

            if (
                "checkout/summary" in next_url
                or not next_url.endswith("/checkout/")
            ):
                next_url = reverse("billing:checkout")

            messages.success(request, "Profile updated successfully.")
            return redirect(next_url)

        messages.error(request, "Please correct the highlighted errors below.")
    else:
        form = InlineProfileForm(instance=rc, initial=initial)

    return render(
        request,
        "customers/complete_profile.html",
        {
            "form": form,
            "show_identity_warning": show_identity_warning,
        },
    )
