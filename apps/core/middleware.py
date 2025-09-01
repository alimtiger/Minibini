from django.contrib.auth import get_user_model, login


class AutoLoginMiddleware:
    """
    Development middleware that automatically logs in a default user.
    
    This bypasses the normal authentication flow for development convenience.
    Remove this middleware when implementing proper authentication.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.User = get_user_model()

    def __call__(self, request):
        # Auto-login if no user is authenticated
        if not request.user.is_authenticated:
            try:
                dev_user = self.User.objects.get(username='dev_user')
                login(request, dev_user)
            except self.User.DoesNotExist:
                # No dev user exists yet - will be created by populate_test_data
                pass
        
        response = self.get_response(request)
        return response