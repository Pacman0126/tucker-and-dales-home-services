import logging
from django.shortcuts import render

# Use __name__ so logs show "core.views"
logger = logging.getLogger(__name__)


def home(request):
    logger.info("Home page accessed")
    return render(request, "core/home.html", {"navbar_mode": "home"})
