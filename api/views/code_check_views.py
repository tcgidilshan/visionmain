from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model

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

            if user.is_staff:  # ✅ If user is active, mark as admin
                return Response(
                    {
                        "id": user.id,
                        "username": user.username,
                        "role": "admin"
                    },
                    status=status.HTTP_200_OK
                )
            else:  # ❌ If not active, deny admin access
                return Response(
                    {"error": "You are not an admin"},
                    status=status.HTTP_403_FORBIDDEN
                )

        except User.DoesNotExist:
            return Response({"error": "You don't have access"}, status=status.HTTP_403_FORBIDDEN)
