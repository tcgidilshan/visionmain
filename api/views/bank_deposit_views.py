from rest_framework.views import APIView
from rest_framework import generics
from rest_framework.filters import OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from ..models import BankDeposit
from ..serializers import BankDepositSerializer
from ..services.safe_service import SafeService
from rest_framework.response import Response


class BankDepositListCreateView(generics.ListCreateAPIView):
    queryset = BankDeposit.objects.select_related('bank_account').all()
    serializer_class = BankDepositSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['branch', 'bank_account', 'date', 'is_confirmed']
    ordering_fields = ['date', 'amount']
    ordering = ['-date']

class BankDepositRetrieveUpdateView(generics.RetrieveUpdateDestroyAPIView):
    queryset = BankDeposit.objects.select_related('bank_account').all()
    serializer_class = BankDepositSerializer

class BankDepositConfirmView(APIView):
    def put(self, request, pk):
        try:
            deposit = BankDeposit.objects.get(pk=pk)

            if deposit.is_confirmed:
                return Response({"message": "Deposit already confirmed"}, status=200)

            # ✅ Mark as confirmed
            deposit.is_confirmed = True
            deposit.save()

            # ✅ Log SafeTransaction (if not already done)
            SafeService.record_transaction(
                branch=deposit.branch,
                amount=deposit.amount,
                transaction_type="deposit",
                reason=f"Bank deposit to {deposit.bank_account.bank_name}",
                reference_id=f"bank-deposit-{deposit.id}"
            )

            return Response({"message": "Deposit confirmed and Safe updated ✅"}, status=200)

        except BankDeposit.DoesNotExist:
            return Response({"error": "Bank deposit not found"}, status=404)
        except Exception as e:
            return Response({"error": str(e)}, status=400)
