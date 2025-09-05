from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from ..models import UserBranch
from django.contrib.auth import get_user_model

CustomUser = get_user_model()

class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user  # Authenticated user from JWT cookie

        # Get branches assigned to this user
        user_branches = UserBranch.objects.filter(user=user).select_related("branch")
        branch_list = [
            {
                "id": ub.branch.id,
                "branch_name": ub.branch.branch_name,
                "location": ub.branch.location,
            }
            for ub in user_branches
        ]

        user_data = {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "mobile": user.mobile,
            "user_code": user.user_code,
            "is_staff": user.is_staff,
            "is_superuser": user.is_superuser,
            "branches": branch_list,
        }

        return Response(user_data)