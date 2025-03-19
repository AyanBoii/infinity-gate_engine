import jwt
from django.conf import settings
from rest_framework import authentication, exceptions
from .models import User

class JWTAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return None
            
        try:
            token = auth_header.split(' ')[1]
            payload = jwt.decode(
                token, 
                settings.JWT_SECRET, 
                algorithms=[settings.JWT_ALGORITHM]
            )
        except jwt.ExpiredSignatureError:
            raise exceptions.AuthenticationFailed('Token expired')
        except (jwt.DecodeError, jwt.InvalidTokenError):
            raise exceptions.AuthenticationFailed('Invalid token')
        except IndexError:
            raise exceptions.AuthenticationFailed('Token prefix missing')
            
        try:
            user = User.objects.get(id=payload['user_id'])
        except User.DoesNotExist:
            raise exceptions.AuthenticationFailed('User not found')
            
        if not user.is_active:
            raise exceptions.AuthenticationFailed('User inactive or deleted')
            
        return (user, token)