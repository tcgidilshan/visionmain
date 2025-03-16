from rest_framework import generics, status
from rest_framework.response import Response
from ..services.user_service import UserService
from django.contrib.auth import get_user_model

CustomUser = get_user_model()

class CreateUserView(generics.CreateAPIView):
    """
    API View to create a user and assign them to multiple branches.
    """

    def create(self, request, *args, **kwargs):
        try:
            data = request.data
            user_data = UserService.create_user(
                username=data.get("username"),
                email=data.get("email"),
                password=data.get("password"),
                user_code=data.get("user_code"),
                mobile=data.get("mobile"),
                first_name=data.get("first_name", ""),
                last_name=data.get("last_name", ""),
                branch_ids=data.get("branch_ids", [])  # ✅ Accept multiple branches as a list
            )

            return Response(
                {
                    "message": "User created successfully",
                    "user": user_data  # ✅ Directly return user dictionary
                },
                status=status.HTTP_201_CREATED
            )
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
