from rest_framework.views import APIView
from rest_framework import generics
from rest_framework.filters import OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from ..models import BankDeposit
from ..serializers import BankDepositSerializer
from ..services.safe_service import SafeService
from rest_framework.response import Response
from django.db import transaction


class BankDepositListCreateView(generics.ListCreateAPIView):
    queryset = BankDeposit.objects.select_related('bank_account').all()
    serializer_class = BankDepositSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['branch', 'bank_account', 'date', 'is_confirmed']
    ordering_fields = ['date', 'amount']
    ordering = ['-date']

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """
        Create a bank deposit and automatically confirm it, updating safe balance.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Set is_confirmed to True automatically
        validated_data = serializer.validated_data
        validated_data['is_confirmed'] = True
        
        # Create the deposit
        deposit = serializer.save()
        
        # Update safe balance by recording the transaction
        try:
            SafeService.record_transaction(
                branch=deposit.branch,
                amount=deposit.amount,
                transaction_type="deposit",
                reason=f"Bank deposit to {deposit.bank_account.bank_name}",
                reference_id=f"bank-deposit-{deposit.id}"
            )
            
            return Response({
                "message": "Bank deposit created and confirmed ✅",
                "data": serializer.data
            }, status=201)
            
        except Exception as e:
            # If safe transaction fails, we should rollback the deposit creation
            raise Response({"error": f"Failed to update safe balance: {str(e)}"}, status=400)


class BankDepositRetrieveUpdateView(generics.RetrieveUpdateDestroyAPIView):
    queryset = BankDeposit.objects.select_related('bank_account').all()
    serializer_class = BankDepositSerializer


# Remove the separate confirmation view since deposits are now auto-confirmed
# class BankDepositConfirmView(APIView):
#     def put(self, request, pk):
#         try:
#             deposit = BankDeposit.objects.get(pk=pk)
#
#             if deposit.is_confirmed:
#                 return Response({"message": "Deposit already confirmed"}, status=200)
#
#             # ✅ Mark as confirmed
#             deposit.is_confirmed = True
#             deposit.save()
#
#             # ✅ Log SafeTransaction (if not already done)
#             SafeService.record_transaction(
#                 branch=deposit.branch,
#                 amount=deposit.amount,
#                 transaction_type="deposit",
#                 reason=f"Bank deposit to {deposit.bank_account.bank_name}",
#                 reference_id=f"bank-deposit-{deposit.id}"
#             )
#
#             return Response({"message": "Deposit confirmed and Safe updated ✅"}, status=200)
#
#         except BankDeposit.DoesNotExist:
#             return Response({"error": "Bank deposit not found"}, status=404)
#         except Exception as e:
#             return Response({"error": str(e)}, status=400)
