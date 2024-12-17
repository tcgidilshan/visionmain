from rest_framework import generics, permissions
from ..models import Branch
from ..serializers import BranchSerializer

# List and Create Branches
class BranchListCreateAPIView(generics.ListCreateAPIView):
    queryset = Branch.objects.all()
    serializer_class = BranchSerializer
    permission_classes = [permissions.IsAuthenticated]

# Retrieve, Update, and Delete a Specific Branch
class BranchRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Branch.objects.only('id', 'branch_name', 'location')
    serializer_class = BranchSerializer
    permission_classes = [permissions.IsAdminUser]
    