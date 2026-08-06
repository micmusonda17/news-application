"""The configuration of my news app."""

from django.apps import AppConfig


class NewsConfig(AppConfig):
    """Config class for the news application."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'news'

    def ready(self):
        """Import the signals file so that my signals start working.

        If I do not import it here django never runs the code inside
        signals.py and then nothing happens when an article is approved.
        """
        import news.signals  # noqa: F401
