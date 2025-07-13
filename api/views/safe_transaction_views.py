from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from ..models import Branch, SafeTransaction
from api.serializers import SafeTransactionSerializer
from api.services.safe_service import SafeService  # adjust path if needed
from api.services.time_zone_convert_service import TimezoneConverterService
from django.db import models

class SafeTransactionView(APIView):
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
    
class SafeIncomeTotalView(APIView):
    def get(self, request):
        branch_id = request.query_params.get("branch")
        from_date = request.query_params.get("from")
        to_date = request.query_params.get("to")

        total_income = SafeService.get_total_income(branch_id, from_date, to_date)

        return Response({"total_income": total_income}, status=status.HTTP_200_OK)
class SafeAll(APIView):
    def get(self, request):
            branch_id = request.query_params.get("branch")
            total_safe = SafeService.get_total_safe(branch_id)
            return Response({"total_balance": total_safe}, status=status.HTTP_200_OK)

class SafeTransactionReportView(APIView):
    """
    GET: Get safe transaction report with filtering by date range and branch
    Query parameters:
    - start_date: YYYY-MM-DD format
    - end_date: YYYY-MM-DD format  
    - branch_id: Branch ID to filter by
    """
    def get(self, request):
        try:
            # Get query parameters
            start_date = request.query_params.get("start_date")
            end_date = request.query_params.get("end_date")
            branch_id = request.query_params.get("branch")
            
            # Convert dates using timezone service
            
            start_datetime, end_datetime = TimezoneConverterService.format_date_with_timezone(
                start_date, end_date
            )
            
            if start_datetime is None or end_datetime is None:
                return Response(
                    {"error": "Invalid date format. Use YYYY-MM-DD format."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Build queryset
            queryset = SafeTransaction.objects.all()
            
            # Filter by branch if provided
            if branch_id:
                queryset = queryset.filter(branch_id=branch_id)
            
            # Filter by date range
            queryset = queryset.filter(
                created_at__gte=start_datetime,
                created_at__lte=end_datetime
            ).order_by('-created_at')
            
            # Calculate totals
            income_total = queryset.filter(transaction_type='income').aggregate(
                total=models.Sum('amount')
            )['total'] or 0
            
            expense_total = queryset.filter(transaction_type='expense').aggregate(
                total=models.Sum('amount')
            )['total'] or 0
            
            deposit_total = queryset.filter(transaction_type='deposit').aggregate(
                total=models.Sum('amount')
            )['total'] or 0
            
            # Serialize transactions
            from api.serializers import SafeTransactionSerializer
            transactions = SafeTransactionSerializer(queryset, many=True).data
            
            # Prepare response
            response_data = {
                "transactions": transactions,
                "summary": {
                    "total_income": str(income_total),
                    "total_expense": str(expense_total),
                    "total_deposit": str(deposit_total),
                    "net_amount": str(income_total - expense_total - deposit_total),
                    "transaction_count": len(transactions)
                },
                "filters": {
                    "start_date": start_date,
                    "end_date": end_date,
                    "branch_id": branch_id
                }
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {"error": f"Failed to generate report: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    

