from rest_framework.views import APIView
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.permissions import BasePermission
from rest_framework import status
from django.contrib.auth import get_user_model
from rest_framework.permissions import AllowAny
from rest_framework.exceptions import PermissionDenied
from ..models import Branch
from ..serializers import BranchSerializer
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from django.conf import settings

User = get_user_model()

# Login View
class LoginView(APIView):
    permission_classes = [AllowAny]  
    def post(self, request):
        
        username = request.data.get('username')
        password = request.data.get('password')

        if not username or not password:
            return Response(
                {"error": "Username and password are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = authenticate(username=username, password=password)

        if user is not None:
            token, created = Token.objects.get_or_create(user=user)
            return Response({
                "message": "Login successful",
                "token": token.key,
                "username": user.username,
                "is_staff": user.is_staff,
                "is_superuser": user.is_superuser,
            })
        else:
            return Response(
                {"error": "Invalid username or password."},
                status=status.HTTP_401_UNAUTHORIZED
            )
# Custom permission for Admin
class IsAdminUser(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_staff

# Admin-only View
class AdminOnlyView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        return Response({"message": "Welcome, Admin!"})

# Custom permission for Super Admin
class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_superuser

# Super Admin-only View
class SuperAdminOnlyView(APIView):
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        return Response({"message": "Hello, Super Admin!"})
    
# Custom permission for admin and super admin
class IsAdminOrSuperAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser)

    
class UserRegistrationView(APIView):
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        email = request.data.get('email')
        mobile = request.data.get('mobile')  # For the custom mobile field

        if not username or not password or not email:
            return Response({"error": "All fields are required!"}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(username=username).exists():
            return Response({"error": "Username already exists!"}, status=status.HTTP_400_BAD_REQUEST)

        # Create a user with the custom user model
        user = User.objects.create_user(username=username, password=password, email=email, mobile=mobile)
        return Response({"message": "User registered successfully!"}, status=status.HTTP_201_CREATED)
    
class AdminRegistrationView(APIView):
    permission_classes = [AllowAny]  # Modify this as needed for extra security

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        email = request.data.get('email')

        if not username or not password or not email:
            return Response({"error": "All fields are required!"}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(username=username).exists():
            return Response({"error": "Username already exists!"}, status=status.HTTP_400_BAD_REQUEST)

        # Create an admin user
        admin_user = User.objects.create_user(username=username, password=password, email=email)
        admin_user.is_staff = True
        admin_user.save()

        return Response({"message": "Admin user registered successfully!"}, status=status.HTTP_201_CREATED)
    
    

