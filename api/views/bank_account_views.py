from rest_framework import generics, status
from rest_framework.response import Response
from ..models import BankAccount
from ..serializers import BankAccountSerializer

class BankAccountListCreateView(generics.ListCreateAPIView):
    """
    Handles listing all bank accounts and creating a new bank account.
    """
    queryset = BankAccount.objects.all()
    serializer_class = BankAccountSerializer

    def list(self, request, *args, **kwargs):
        """
        List all bank accounts with optional filtering (e.g., by bank name or account number).
        """
        queryset = self.get_queryset()

        # Optional filtering by bank name, account number, or branch
        bank_name_filter = request.query_params.get('bank_name')
        account_number_filter = request.query_params.get('account_number')
        branch_id_filter = request.query_params.get('branch_id')

        if bank_name_filter:
            queryset = queryset.filter(bank_name__icontains=bank_name_filter)
        if account_number_filter:
            queryset = queryset.filter(account_number__icontains=account_number_filter)
        if branch_id_filter:
            queryset = queryset.filter(branch_id=branch_id_filter)

        # Pagination is automatically handled by DRF
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        """
        Create a new bank account entry.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class BankAccountRetrieveUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    """
    Handles retrieving, updating, and deleting a bank account by ID.
    """
    queryset = BankAccount.objects.all()
    serializer_class = BankAccountSerializer
    lookup_field = 'id'  

    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve a bank account by ID.
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        """
        Update an existing bank account (partial or full).
        """
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        """
        Delete a bank account by ID.
        """
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)