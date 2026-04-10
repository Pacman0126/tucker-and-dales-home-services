from django.conf import settings
from django.http import HttpResponsePermanentRedirect


class CanonicalHostRedirectMiddleware:
    """
    Redirect non-canonical hosts to the public canonical host.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.canonical_host = getattr(
            settings,
            "CANONICAL_HOST",
            "www.tuckeranddales.com",
        ).strip().lower()

        self.redirect_hosts = {
            "tucker-and-dales-home-services-51862a9ae5a8.herokuapp.com",
            "tuckeranddales.com",
        }

    def __call__(self, request):
        host = request.get_host().split(":")[0].lower()

        if host in self.redirect_hosts and host != self.canonical_host:
            return HttpResponsePermanentRedirect(
                f"https://{self.canonical_host}{request.get_full_path()}"
            )

        return self.get_response(request)
