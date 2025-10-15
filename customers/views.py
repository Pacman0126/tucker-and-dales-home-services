from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import login
from django.contrib import messages

from .models import RegisteredCustomer
from .forms import RegisteredCustomerForm
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
    """Allow new customers to create accounts."""
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(
                request, "🎉 Account created successfully! You are now logged in.")
            return redirect("home")
    else:
        form = UserCreationForm()
    return render(request, "customers/register.html", {"form": form})
