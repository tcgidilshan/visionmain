from rest_framework import generics, permissions
from ..models import Branch
from ..serializers import BranchSerializer
from ..services.role_service import get_user_role

RESTRICTED_BRANCH_IDS = [4]


def _branch_queryset(user):
    role = get_user_role(user)
    all_branches = Branch.objects.all()
    if role in ("SUPERUSER", "ADMINPRO"):
        return all_branches
    return all_branches.exclude(id__in=RESTRICTED_BRANCH_IDS)


# List and Create Branches
class BranchListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = BranchSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return _branch_queryset(self.request.user)


# Retrieve, Update, and Delete a Specific Branch
class BranchRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = BranchSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return _branch_queryset(self.request.user)
    