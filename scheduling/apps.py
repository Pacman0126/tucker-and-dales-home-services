from django.apps import AppConfig


class SchedulingConfig(AppConfig):
    name = "scheduling"

    def ready(self):
        import scheduling.signals  # noqa
