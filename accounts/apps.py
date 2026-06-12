from django.apps import AppConfig

class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'   # replace with your actual app name

    def ready(self):
        import accounts.signals  # replace with your actual app name