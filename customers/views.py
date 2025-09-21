from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .models import RegisteredCustomer
from .forms import RegisteredCustomerForm

# Create your views here.


def customer_list(request):
    customers = RegisteredCustomer.objects.all()
    return render(request, "customers/customer_list.html", {"customers": customers})


def customer_detail(request, pk):
    customer = get_object_or_404(RegisteredCustomer, pk=pk)
    return render(request, "customers/customer_detail.html", {"customer": customer})


def customer_create(request):
    if request.method == "POST":
        form = RegisteredCustomerForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Customer registered successfully.")
            return redirect("customers:customer_list")
    else:
        form = RegisteredCustomerForm()
    return render(request, "customers/customer_form.html", {"form": form})
