from django.apps import AppConfig


class NavigationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "navigation"

    def ready(self):
        """注册信号处理器"""
        import navigation.signals  # noqa
