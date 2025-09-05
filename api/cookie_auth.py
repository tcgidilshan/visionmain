from rest_framework.authentication import TokenAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, AuthenticationFailed

# Keep your existing class
class CookieTokenAuthentication(TokenAuthentication):
    def authenticate(self, request):
        token = request.COOKIES.get('auth_token')
        if not token:
            return None
        return self.authenticate_credentials(token)

# Add the new JWT class
class CookieJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        # Get token from cookie
        token = request.COOKIES.get('access_token')
        
        if not token:
            return None
        
        try:
            # Validate token
            validated_token = self.get_validated_token(token)
            user = self.get_user(validated_token)
            return (user, validated_token)
        except (InvalidToken, AuthenticationFailed):
            return None