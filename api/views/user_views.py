from rest_framework import generics, status
from rest_framework.response import Response
from ..services.user_service import UserService
from django.contrib.auth import get_user_model
from ..serializers import UserBranchSerializer
from ..models import UserBranch
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

class UpdateUserView(generics.UpdateAPIView):
    """
    API View to update a user's details.
    """

    def put(self, request, user_id):
        try:
            data = request.data
            user = UserService.update_user(
                user_id=user_id,
                username=data.get("username"),
                email=data.get("email"),
                user_code=data.get("user_code"),
                mobile=data.get("mobile"),
                first_name=data.get("first_name"),
                last_name=data.get("last_name"),
                branch_ids=data.get("branch_ids", [])
            )

            return Response(
                {
                    "message": "User updated successfully",
                    "user": {
                        "id": user.id,
                        "username": user.username,
                        "email": user.email,
                        "user_code": user.user_code,
                        "mobile": user.mobile,
                        "first_name": user.first_name,
                        "last_name": user.last_name,
                        "branches_assigned": [ub.branch.id for ub in user.user_branches.all()]
                    }
                },
                status=status.HTTP_200_OK
            )
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
class GetAllUsersView(generics.ListAPIView):
    """
    API View to get all user-branch assignments.
    """
    queryset = UserBranch.objects.all()
    serializer_class = UserBranchSerializer
 
    