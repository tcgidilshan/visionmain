from rest_framework.views import APIView
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.permissions import BasePermission
from rest_framework import status
from django.contrib.auth import get_user_model
from rest_framework.permissions import AllowAny
from rest_framework.exceptions import PermissionDenied
from ..models import Branch,UserBranch
from ..serializers import BranchSerializer
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken  # Add this import

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
            # Generate JWT tokens instead of simple token
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            
            branches = UserBranch.objects.filter(user_id=user.id).select_related("branch")
            branch_details = [
                {
                    "id": ub.branch.id,
                    "branch_name": ub.branch.branch_name,
                    "location": ub.branch.location,
                }
                for ub in branches
            ]

            response = Response({
                "message": "Login successful",
                "username": user.username,
                "is_staff": user.is_staff,
                "is_superuser": user.is_superuser,
                "branches": branch_details
            })
            
            response.set_cookie(
                key="access_token",
                value=access_token,
                httponly=True,
                secure=True,  # Set to True in production
                samesite="None",
                max_age=60*60*24*7  # 7 days
            )
            
            response.set_cookie(
                key="refresh_token",
                value=str(refresh),
                httponly=True,
                secure=True,  # Set to True in production
                samesite="None",
                max_age=60*60*24*30  # 7 days
            )
            
            return response
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
    permission_classes = [AllowAny] 
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
        username = request.data.get("username")
        password = request.data.get("password")
        email = request.data.get("email")
        first_name = request.data.get("first_name", "")
        last_name = request.data.get("last_name", "")
        mobile = request.data.get("mobile", None)
        user_code = request.data.get("user_code", None)

        if not username or not password or not email or not user_code:
            return Response({"error": "Username, password, email, and user_code are required!"}, status=status.HTTP_400_BAD_REQUEST)
        if User.objects.filter(username=username).exists():
            return Response({"error": "Username already exists!"}, status=status.HTTP_400_BAD_REQUEST)
        if User.objects.filter(email=email).exists():
            return Response({"error": "Email already exists!"}, status=status.HTTP_400_BAD_REQUEST)
        if User.objects.filter(user_code=user_code).exists():
            return Response({"error": "User code already exists!"}, status=status.HTTP_400_BAD_REQUEST)

        # ✅ Create an admin user
        admin_user = User.objects.create_user(
            username=username,
            password=password,
            email=email,
            first_name=first_name,
            last_name=last_name,
            mobile=mobile,
            user_code=user_code,
        )
        admin_user.is_staff = True  # ✅ Admin permissions
        admin_user.is_superuser = True  # ✅ Optional: Give superuser rights
        admin_user.save()

        # ✅ Assign user to all branches
        all_branches = Branch.objects.all()
        user_branches = [UserBranch(user=admin_user, branch=branch) for branch in all_branches]
        UserBranch.objects.bulk_create(user_branches)  # ✅ Efficient batch insert

        return Response(
            {
                "message": "Admin user registered successfully!",
                "user": {
                    "id": admin_user.id,
                    "username": admin_user.username,
                    "email": admin_user.email,
                    "first_name": admin_user.first_name,
                    "last_name": admin_user.last_name,
                    "mobile": admin_user.mobile,
                    "user_code": admin_user.user_code,
                    "branches_assigned": [branch.id for branch in all_branches]
                }
            },
            status=status.HTTP_201_CREATED
        )

class LogoutView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        response = Response({"message": "Logout successful."}, status=status.HTTP_200_OK)
        # Remove tokens from cookies
        response.delete_cookie("access_token", samesite="None")
        response.delete_cookie("refresh_token", samesite="None")
        return response




