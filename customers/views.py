import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .models import RegisteredCustomer
from .forms import RegisteredCustomerForm

# Use __name__ so logs show "customers.views"
logger = logging.getLogger(__name__)


def customer_list(request):
    logger.info("Customer list page accessed")
    customers = RegisteredCustomer.objects.all()
    logger.debug(f"Fetched {customers.count()} customers from database")
    return render(request, "customers/customer_list.html", {"customers": customers})


def customer_detail(request, pk):
    logger.info(f"Customer detail page accessed for ID={pk}")
    customer = get_object_or_404(RegisteredCustomer, pk=pk)
    return render(request, "customers/customer_detail.html", {"customer": customer})


def customer_create(request):
    if request.method == "POST":
        form = RegisteredCustomerForm(request.POST)
        if form.is_valid():
            customer = form.save()
            logger.info(
                f"New customer created: {customer.first_name} {customer.last_name} (ID={customer.pk})")
            messages.success(request, "Customer registered successfully.")
            return redirect("customers:customer_list")
        else:
            logger.warning("Customer form submission failed validation")
    else:
        logger.debug("Customer create form displayed")
        form = RegisteredCustomerForm()

    return render(request, "customers/customer_form.html", {"form": form})
