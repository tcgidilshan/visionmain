from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from ..services.user_service import UserService
from django.contrib.auth import get_user_model
from ..models import UserBranch
CustomUser = get_user_model()
from rest_framework.permissions import IsAuthenticated
from ..services.pagination_service import PaginationService
from django.db.models import Q
class CreateUserView(generics.CreateAPIView):
    """
    API View to create a user and assign them to multiple branches.
    """

    def create(self, request, *args, **kwargs):
        try:
            data = request.data
            mobile = data.get("mobile")
            if not mobile:
                return Response({"error": "Mobile number is required"}, status=status.HTTP_400_BAD_REQUEST)
            user_data = UserService.create_user(
                username=data.get("username"),
                email=data.get("email"),
                password=data.get("password"),
                user_code=data.get("user_code"),
                mobile=mobile,
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
    permission_classes = [IsAuthenticated]

    def put(self, request, user_id):
        try:
            # ✅ Check permissions
            if not request.user.is_superuser and not request.user.is_staff:
                return Response({"error": "You do not have permission to update users."}, status=status.HTTP_403_FORBIDDEN)
            
            user = CustomUser.objects.get(id=user_id)
            
            # ✅ Admin can only update regular users
            if request.user.is_staff and not request.user.is_superuser:
                if user.is_staff or user.is_superuser:
                    return Response({"error": "Admins can only update regular user profiles."}, status=status.HTTP_403_FORBIDDEN)
            
            data = request.data
            
            # ✅ Handle role changes (only superuser can do this)
            if "role" in data and request.user.is_superuser:
                role = data.get("role")
                if role == "Superuser":
                    user.is_superuser = True
                    user.is_staff = True
                elif role == "Admin":
                    user.is_superuser = False
                    user.is_staff = True
                elif role == "User":
                    user.is_superuser = False
                    user.is_staff = False
                user.save()
            
            # ✅ Handle is_active changes (only superuser can deactivate)
            if "is_active" in data and request.user.is_superuser:
                user.is_active = data["is_active"]
                user.save()
            
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
                        "role": "Superuser" if user.is_superuser else ("Admin" if user.is_staff else "User"),
                        "is_active": user.is_active,
                        "branches_assigned": [ub.branch.id for ub in user.user_branches.all()]
                    }
                },
                status=status.HTTP_200_OK
            )
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
class GetAllUsersView(APIView):
    permission_classes = [IsAuthenticated]
    """
    API View to get all user-branch assignments.
    """
    def get(self, request):
            # ✅ Check if the user is a superuser
            if not request.user.is_superuser:
                return Response({"error": "You do not have permission to access this resource."}, status=status.HTTP_403_FORBIDDEN)

            users = CustomUser.objects.all()

            # Add search functionality
            search = request.GET.get('search')
            if search:
                search_lower = search.lower()
                role_filter = Q()
                if search_lower == 'superuser':
                    role_filter = Q(is_superuser=True)
                elif search_lower == 'admin':
                    role_filter = Q(is_staff=True, is_superuser=False)
                elif search_lower == 'user':
                    role_filter = Q(is_staff=False, is_superuser=False)
                
                users = users.filter(
                    Q(username__icontains=search) | 
                    Q(user_code__icontains=search) | 
                    role_filter
                )

            user_list = []
            for user in users:
                # ✅ Get all branches assigned to the user
                branches = UserBranch.objects.filter(user_id=user.id).select_related("branch")

                branch_details = [
                    {
                        "id": ub.branch.id,
                        "branch_name": ub.branch.branch_name,  # Change if needed
                    }
                    for ub in branches
                ]

                user_list.append({
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "user_code": user.user_code,
                    "mobile": user.mobile,  # ✅ Added mobile number
                    "role": "Superuser" if user.is_superuser else ("Admin" if user.is_staff else "User"),
                    "is_staff": user.is_staff,
                    "is_superuser": user.is_superuser,
                    "is_active": user.is_active,
                    "branches": branch_details,  # ✅ Add branch list
                })

            # Use pagination
            paginator = PaginationService()
            paginated_users = paginator.paginate_queryset(user_list, request)
            return paginator.get_paginated_response(paginated_users)

class GetSingleUserView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, user_id):
        # ✅ Check permissions based on role
        if not request.user.is_superuser and not request.user.is_staff:
            return Response({"error": "You do not have permission to access this resource."}, status=status.HTTP_403_FORBIDDEN)

        user = CustomUser.all_objects.filter(is_active=True).get(id=user_id)
        
        # ✅ Admin can only view regular users
        if request.user.is_staff and not request.user.is_superuser:
            if user.is_staff or user.is_superuser:
                return Response({"error": "Admins can only view regular user profiles."}, status=status.HTTP_403_FORBIDDEN)

        branches = UserBranch.objects.filter(user_id=user.id).select_related("branch")

        branch_details = [
            {
                "id": ub.branch.id,
                "branch_name": ub.branch.branch_name,  # Change if needed
            }
            for ub in branches
        ]

        return Response({
            "id": user.id,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "mobile": user.mobile,
            "email": user.email,
            "user_code": user.user_code,
            "role": "Superuser" if user.is_superuser else ("Admin" if user.is_staff else "User"),
            "is_staff": user.is_staff,
            "is_superuser": user.is_superuser,
            "is_active": user.is_active,
            "branches": branch_details
        })
