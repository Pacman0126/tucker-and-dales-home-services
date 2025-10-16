from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import login
from django.contrib import messages

from .models import RegisteredCustomer
from .forms import CustomerProfileForm
from .forms import RegisteredCustomerForm
from .forms import CustomerRegistrationForm
import logging


logger = logging.getLogger(__name__)


def superuser_required(user):
    return user.is_authenticated and user.is_superuser


# 🔹 Customer list (search + pagination, superuser only)
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


# 🔹 Detail (view only)
@login_required
@user_passes_test(superuser_required)
def customer_detail(request, pk):
    customer = get_object_or_404(RegisteredCustomer, pk=pk)
    return render(request, "customers/customer_detail.html", {"customer": customer})


# 🔹 Edit customer
@login_required
@user_passes_test(superuser_required)
def customer_edit(request, pk):
    customer = get_object_or_404(RegisteredCustomer, pk=pk)

    if request.method == "POST":
        form = RegisteredCustomerForm(request.POST, instance=customer)
        if form.is_valid():
            form.save()
            logger.info(f"Customer {customer.pk} updated by {request.user}")
            messages.success(request, "Customer updated successfully.")
            return redirect("customers:customer_detail", pk=customer.pk)
    else:
        form = RegisteredCustomerForm(instance=customer)

    return render(
        request, "customers/customer_form.html", {
            "form": form, "customer": customer}
    )


# 🔹 Delete customer (with confirmation page)
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


def register(request):
    if request.method == "POST":
        form = CustomerRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # 🪄 Create linked RegisteredCustomer profile automatically
            RegisteredCustomer.objects.create(
                user=user,
                first_name=form.cleaned_data["first_name"],
                last_name=form.cleaned_data["last_name"],
                email=form.cleaned_data["email"],
                street_address="",
                city="",
                state="",
                zipcode="",
                phone="",
                region="Unknown"
            )
            login(request, user)
            messages.success(
                request, f"Welcome, {user.username}! Please complete your profile.")
            return redirect("customers:complete_profile")
    else:
        form = CustomerRegistrationForm()

    return render(request, "customers/register.html", {"form": form})


@login_required
def complete_profile(request):
    # If user already has a profile, skip to checkout
    if hasattr(request.user, "customer_profile"):
        return redirect("billing:checkout")

    if request.method == "POST":
        form = CustomerProfileForm(request.POST)
        if form.is_valid():
            profile = form.save(commit=False)
            profile.user = request.user
            profile.save()
            return redirect("billing:checkout")  # go straight to Stripe
    else:
        form = CustomerProfileForm()

    return render(request, "customers/complete_profile.html", {"form": form})
