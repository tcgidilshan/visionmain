from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model,authenticate

User = get_user_model()  # Get CustomUser dynamically

class UserCodeCheckView(APIView):
    """
    API View to check if a user_code exists and return user details.
    """

    def post(self, request):
        user_code = request.data.get("user_code")

        if not user_code:
            return Response({"error": "User code is required!"}, status=status.HTTP_400_BAD_REQUEST)

        # ✅ Check if user with given user_code exists
        try:
            user = User.objects.get(user_code=user_code)
            return Response(
                {
                    "id": user.id,
                    "username": user.username
                },
                status=status.HTTP_200_OK
            )
        except User.DoesNotExist:
            return Response({"error": "You don't have access"}, status=status.HTTP_403_FORBIDDEN)
        
class AdminCodeCheckView(APIView):
    """
    API View to check if a user_code exists and return user details with admin role if active.
    """

    def post(self, request):
        user_code = request.data.get("user_code")

        if not user_code:
            return Response({"error": "User code is required!"}, status=status.HTTP_400_BAD_REQUEST)

        # ✅ Check if user with given user_code exists
        try:
            user = User.objects.get(user_code=user_code)

            if user.is_staff or user.is_admin_pro:
                role = "adminpro" if user.is_admin_pro else "admin"
                return Response(
                    {
                        "id": user.id,
                        "username": user.username,
                        "role": role
                    },
                    status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {"error": "You are not an admin"},
                    status=status.HTTP_403_FORBIDDEN
                )

        except User.DoesNotExist:
            return Response({"error": "You don't have access"}, status=status.HTTP_403_FORBIDDEN)
class AllRoleCheckView(APIView):
    """
    Unified API to check user_code and return:
    - User details + role (admin/user)
    - Error if invalid/no access
    """
    
    def post(self, request):
        user_code = request.data.get("user_code")
        password = request.data.get("password")
        if not user_code:
            return Response(
                {"error": "user_code is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(user_code=user_code)
               # Authenticate the user with password
            authenticated_user = authenticate(
                request, 
                username=user.username, 
                password=password
            )
            if not authenticated_user:
                return Response(
                    {"error": "Invalid password"},
                    status=status.HTTP_403_FORBIDDEN
                )
            if user.is_superuser:
                role = "superuser"
            elif user.is_admin_pro:
                role = "adminpro"
            elif user.is_staff:
                role = "admin"
            else:
                role = "user"
            
            return Response(
                {
                    "id": user.id,
                    "username": user.username,
                    "role": role,
                },
                status=status.HTTP_200_OK
            )
            
        except User.DoesNotExist:
            return Response(
                {"error": "Invalid user_code or no access"},
                status=status.HTTP_403_FORBIDDEN
            )