# customers/views.py
import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import RegisteredCustomer
from .forms import RegisteredCustomerForm

logger = logging.getLogger(__name__)


def customer_list(request):
    customers = RegisteredCustomer.objects.all()
    logger.info("Customer list accessed")
    return render(request, "customers/customer_list.html", {"customers": customers})


def customer_detail(request, pk):
    customer = get_object_or_404(RegisteredCustomer, pk=pk)
    return render(request, "customers/customer_detail.html", {"customer": customer})

# Superuser check


def is_owner(user):
    return user.is_superuser


@login_required
@user_passes_test(is_owner)
def customer_edit(request, pk):
    customer = get_object_or_404(RegisteredCustomer, pk=pk)
    if request.method == "POST":
        form = RegisteredCustomerForm(request.POST, instance=customer)
        if form.is_valid():
            form.save()
            logger.info(f"Customer {customer.id} updated by {request.user}")
            return redirect("customers:customer_detail", pk=customer.pk)
    else:
        form = RegisteredCustomerForm(instance=customer)
    return render(request, "customers/customer_edit.html", {"form": form, "customer": customer})
