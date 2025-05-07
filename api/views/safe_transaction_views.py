from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from api.models import Branch, SafeTransaction
from api.serializers import SafeTransactionSerializer
from api.services.safe_service import SafeService  # adjust path if needed

class SafeTransaction(APIView):
    """
    POST: Record a new safe transaction (income / expense / deposit)
    Automatically updates SafeBalance.
    """
    def post(self, request, *args, **kwargs):
        serializer = SafeTransactionSerializer(data=request.data)
        if serializer.is_valid():
            try:
                branch = serializer.validated_data["branch"]
                amount = serializer.validated_data["amount"]
                transaction_type = serializer.validated_data["transaction_type"]
                reason = serializer.validated_data.get("reason", "")
                reference_id = serializer.validated_data.get("reference_id", None)

                # Record using service
                updated_balance = SafeService.record_transaction(
                    branch=branch,
                    amount=amount,
                    transaction_type=transaction_type,
                    reason=reason,
                    reference_id=reference_id,
                )

                return Response({
                    "message": "Transaction recorded successfully.",
                    "safe_balance": str(updated_balance.balance)
                }, status=status.HTTP_201_CREATED)

            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
