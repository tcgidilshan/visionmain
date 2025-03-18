from django.contrib.auth import get_user_model
from django.db import transaction
from ..models import Branch, UserBranch

CustomUser = get_user_model()  # Get the custom user model dynamically

class UserService:
    @staticmethod
    @transaction.atomic
    def create_user(username, email, password, user_code, mobile=None, first_name="", last_name="", branch_ids=None):
        """
        Create a new user and assign them to multiple branches.
        """
        if CustomUser.objects.filter(username=username).exists():
            raise ValueError("Username already exists")
        if CustomUser.objects.filter(email=email).exists():
            raise ValueError("Email already exists")
        if CustomUser.objects.filter(user_code=user_code).exists():
            raise ValueError("User code already exists")

        # ✅ Create user
        user = CustomUser.objects.create_user(
            username=username,
            email=email,
            password=password,
            user_code=user_code,
            mobile=mobile,
            first_name=first_name,
            last_name=last_name,
        )

        # ✅ Assign user to multiple branches if branch_ids exist
        if branch_ids:
            branches = Branch.objects.filter(id__in=branch_ids)
            if not branches.exists():
                raise ValueError("No valid branches found")

            user_branches = [UserBranch(user=user, branch=branch) for branch in branches]
            UserBranch.objects.bulk_create(user_branches)

        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "user_code": user.user_code,
            "mobile": user.mobile,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "branches": [branch.id for branch in branches] if branch_ids else []
        }
    
    @staticmethod
    @transaction.atomic
    def update_user(user_id, username=None, email=None, user_code=None, mobile=None, first_name=None, last_name=None, branch_ids=None):
        """
        Update an existing user's details, including their branch assignments.
        """
        try:
            user = CustomUser.objects.get(id=user_id)
        except CustomUser.DoesNotExist:
            raise ValueError("User not found")

        # ✅ Update user fields only if values are provided
        if username:
            if CustomUser.objects.filter(username=username).exclude(id=user_id).exists():
                raise ValueError("Username already exists")
            user.username = username

        if email:
            if CustomUser.objects.filter(email=email).exclude(id=user_id).exists():
                raise ValueError("Email already exists")
            user.email = email

        if user_code:
            if CustomUser.objects.filter(user_code=user_code).exclude(id=user_id).exists():
                raise ValueError("User code already exists")
            user.user_code = user_code

        if mobile is not None:
            user.mobile = mobile

        if first_name is not None:
            user.first_name = first_name

        if last_name is not None:
            user.last_name = last_name

        user.save()  # ✅ Save the updated user details

        # ✅ Handle branch reassignment if `branch_ids` is provided
        if branch_ids is not None:
            branches = Branch.objects.filter(id__in=branch_ids)
            if not branches.exists():
                raise ValueError("No valid branches found")

            # ✅ Remove existing branch assignments
            UserBranch.objects.filter(user=user).delete()

            # ✅ Assign new branches
            user_branches = [UserBranch(user=user, branch=branch) for branch in branches]
            UserBranch.objects.bulk_create(user_branches)

        return user
