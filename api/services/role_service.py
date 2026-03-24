from django.contrib.auth.base_user import AbstractBaseUser


def get_user_role(user: AbstractBaseUser) -> str:
    """
    Returns the role keyword for a given user.

    Priority order:
        is_superuser  → "SUPERUSER"
        is_admin_pro  → "ADMINPRO"
        is_staff      → "ADMIN"
        (none)        → "USER"
    """
    if getattr(user, 'is_superuser', False):
        return "SUPERUSER"
    if getattr(user, 'is_admin_pro', False):
        return "ADMINPRO"
    if getattr(user, 'is_staff', False):
        return "ADMIN"
    return "USER"
