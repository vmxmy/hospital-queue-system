from debug_toolbar.middleware import DebugToolbarMiddleware

class PatchedDebugToolbarMiddleware(DebugToolbarMiddleware):
    """
    修复Debug Toolbar中间件，确保toolbar变量正确传递到模板上下文
    """
    def process_template_response(self, request, response):
        if hasattr(response, "context_data") and response.context_data is not None:
            response.context_data["toolbar"] = getattr(request, "toolbar", None)
        return super().process_template_response(request, response)
