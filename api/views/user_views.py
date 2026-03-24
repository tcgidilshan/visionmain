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
from ..services.role_service import get_user_role
from ..views.branch_views import RESTRICTED_BRANCH_IDS


def _get_scoped_user(req_user, user_id):
    """
    Fetch target user scoped by the requesting user's role.
    Raises CustomUser.DoesNotExist if the ID is outside the requester's allowed scope,
    producing a 404 instead of leaking that the record exists.
    """
    if req_user.is_superuser:
        return CustomUser.objects.get(id=user_id)
    else:
        # Admin and AdminPro: Admin + User levels only (no Superuser, no AdminPro)
        return CustomUser.objects.get(id=user_id, is_superuser=False, is_admin_pro=False)
class CreateUserView(generics.CreateAPIView):
    """
    API View to create a user and assign them to multiple branches.
    """
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        req_user = request.user
        if not (req_user.is_superuser or req_user.is_admin_pro or req_user.is_staff):
            return Response({"error": "You do not have permission to create users."}, status=status.HTTP_403_FORBIDDEN)

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
        req_user = request.user
        if not (req_user.is_superuser or req_user.is_admin_pro or req_user.is_staff):
            return Response({"error": "You do not have permission to update users."}, status=status.HTTP_403_FORBIDDEN)

        try:
            user = _get_scoped_user(req_user, user_id)
        except CustomUser.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            
            data = request.data
            
            # ✅ Handle role changes (superuser can set all roles; adminpro can only set Admin/User)
            if "role" in data and (request.user.is_superuser or request.user.is_admin_pro):
                role = data.get("role")
                # AdminPro cannot assign Superuser or AdminPro roles
                if not request.user.is_superuser and role in ("Superuser", "AdminPro"):
                    return Response({"error": "You do not have permission to assign this role."}, status=status.HTTP_403_FORBIDDEN)
                if role == "Superuser":
                    user.is_superuser = True
                    user.is_staff = True
                    user.is_admin_pro = False
                elif role == "AdminPro":
                    user.is_superuser = False
                    user.is_staff = False
                    user.is_admin_pro = True
                elif role == "Admin":
                    user.is_superuser = False
                    user.is_staff = True
                    user.is_admin_pro = False
                elif role == "User":
                    user.is_superuser = False
                    user.is_staff = False
                    user.is_admin_pro = False
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
                        "role": "Superuser" if user.is_superuser else ("AdminPro" if user.is_admin_pro else ("Admin" if user.is_staff else "User")),
                        "is_admin_pro": user.is_admin_pro,
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
            req_user = request.user

            # Only superuser, adminpro, and admin can access this view
            if not (req_user.is_superuser or req_user.is_admin_pro or req_user.is_staff):
                return Response({"error": "You do not have permission to access this resource."}, status=status.HTTP_403_FORBIDDEN)

            # Role-based base queryset
            if req_user.is_superuser:
                # Superuser sees everyone
                users = CustomUser.objects.all()
            else:
                # Admin and AdminPro see Admin + User levels only (no Superuser, no AdminPro)
                users = CustomUser.objects.filter(is_superuser=False, is_admin_pro=False)

            # Add search functionality
            search = request.GET.get('search')
            if search:
                search_lower = search.lower()
                role_filter = Q()
                if search_lower == 'superuser' and req_user.is_superuser:
                    role_filter = Q(is_superuser=True)
                elif search_lower == 'adminpro' and req_user.is_superuser:
                    role_filter = Q(is_admin_pro=True, is_superuser=False)
                elif search_lower == 'admin' and (req_user.is_superuser or req_user.is_admin_pro or req_user.is_staff):
                    role_filter = Q(is_staff=True, is_superuser=False, is_admin_pro=False)
                elif search_lower == 'user':
                    role_filter = Q(is_staff=False, is_superuser=False, is_admin_pro=False)

                users = users.filter(
                    Q(username__icontains=search) |
                    Q(user_code__icontains=search) |
                    role_filter
                )

            viewer_role = get_user_role(req_user)
            user_list = []
            for user in users:
                branches = UserBranch.objects.filter(user_id=user.id).select_related("branch")

                branch_details = [
                    {
                        "id": ub.branch.id,
                        "branch_name": ub.branch.branch_name,
                    }
                    for ub in branches
                    if viewer_role in ("SUPERUSER", "ADMINPRO") or ub.branch.id not in RESTRICTED_BRANCH_IDS
                ]

                user_list.append({
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "user_code": user.user_code,
                    "mobile": user.mobile,  # ✅ Added mobile number
                    "role": "Superuser" if user.is_superuser else ("AdminPro" if user.is_admin_pro else ("Admin" if user.is_staff else "User")),
                    "is_staff": user.is_staff,
                    "is_superuser": user.is_superuser,
                    "is_admin_pro": user.is_admin_pro,
                    "is_active": user.is_active,
                    "branches": branch_details,
                })

            # Use pagination
            paginator = PaginationService()
            paginated_users = paginator.paginate_queryset(user_list, request)
            return paginator.get_paginated_response(paginated_users)

class GetSingleUserView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, user_id):
        req_user = request.user
        if not (req_user.is_superuser or req_user.is_admin_pro or req_user.is_staff):
            return Response({"error": "You do not have permission to access this resource."}, status=status.HTTP_403_FORBIDDEN)

        try:
            user = _get_scoped_user(req_user, user_id)
        except CustomUser.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        branches = UserBranch.objects.filter(user_id=user.id).select_related("branch")
        viewer_role = get_user_role(req_user)

        branch_details = [
            {
                "id": ub.branch.id,
                "branch_name": ub.branch.branch_name,
            }
            for ub in branches
            if viewer_role in ("SUPERUSER", "ADMINPRO") or ub.branch.id not in RESTRICTED_BRANCH_IDS
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
            "role": "Superuser" if user.is_superuser else ("AdminPro" if user.is_admin_pro else ("Admin" if user.is_staff else "User")),
            "is_staff": user.is_staff,
            "is_superuser": user.is_superuser,
            "is_admin_pro": user.is_admin_pro,
            "is_active": user.is_active,
            "branches": branch_details
        })
