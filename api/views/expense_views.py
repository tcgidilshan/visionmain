# views.py

from rest_framework import generics,status
from ..models import ExpenseMainCategory, ExpenseSubCategory,Expense
from ..serializers import ExpenseMainCategorySerializer, ExpenseSubCategorySerializer,ExpenseSerializer,ExpenseReportSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from ..services.expense_validation_service import ExpenseValidationService
from ..services.safe_service import SafeService
from django.db.models import Sum
from django.utils.dateparse import parse_date
from django.db import transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from decimal import Decimal

# ---------- Main Category Views ----------
class ExpenseMainCategoryListCreateView(generics.ListCreateAPIView):
    queryset = ExpenseMainCategory.objects.all()
    serializer_class = ExpenseMainCategorySerializer

class ExpenseMainCategoryRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ExpenseMainCategory.objects.all()
    serializer_class = ExpenseMainCategorySerializer

# ---------- Sub Category Views ----------
class ExpenseSubCategoryListCreateView(generics.ListCreateAPIView):
    queryset = ExpenseSubCategory.objects.select_related('main_category').all()
    serializer_class = ExpenseSubCategorySerializer
class ExpenseSubCategoryRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ExpenseSubCategory.objects.all()
    serializer_class = ExpenseSubCategorySerializer
class ExpenseCreateView(APIView):
    def post(self, request):
        serializer = ExpenseSerializer(data=request.data)
        if serializer.is_valid():
            branch_id = serializer.validated_data['branch'].id
            amount = serializer.validated_data['amount']
            paid_source = serializer.validated_data.get("paid_source", "safe")

            try:
                # 🛡️ Validate safe balance if paid from safe
                if paid_source == "safe":
                    SafeService.validate_sufficient_balance(branch_id, amount)
                else:
                    ExpenseValidationService.validate_expense_limit(branch_id, amount)

                expense = serializer.save()

                # 💾 Record safe transaction if needed
                if paid_source == "safe":
                    SafeService.record_transaction(
                        branch=expense.branch,
                        amount=expense.amount,
                        transaction_type='expense',
                        reason=f"{expense.main_category.name} - {expense.sub_category.name}",
                        reference_id=f"expense-{expense.id}"
                    )

                return Response(ExpenseSerializer(expense).data, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class ExpenseReportView(APIView):
    def get(self, request):
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        branch_id = request.query_params.get('branch_id')

        if not start_date or not end_date or not branch_id:
            return Response({
                "error": "start_date, end_date, and branch_id are required."
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Convert to date objects
            start_date_obj = parse_date(start_date)
            end_date_obj = parse_date(end_date)

            queryset = Expense.objects.select_related('main_category', 'sub_category').filter(
                created_at__date__range=[start_date_obj, end_date_obj],
                branch_id=branch_id
            ).order_by('-created_at')

            total = queryset.aggregate(total_expense=Sum('amount'))['total_expense'] or 0

            return Response({
                "total_expense": total,
                "expenses": ExpenseReportSerializer(queryset, many=True).data
            })

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class ExpenseUpdateView(APIView):
    def put(self, request, pk):
        try:
            expense = Expense.objects.get(pk=pk)
        except Expense.DoesNotExist:
            return Response({"error": "Expense not found."}, status=status.HTTP_404_NOT_FOUND)

        old_amount = expense.amount
        old_paid_source = expense.paid_source
        serializer = ExpenseSerializer(expense, data=request.data, partial=True)

        if serializer.is_valid():
            new_amount = Decimal(str(serializer.validated_data.get('amount', expense.amount)))
            new_paid_source = serializer.validated_data.get('paid_source', expense.paid_source)
            branch_id = serializer.validated_data.get('branch', expense.branch).id

            try:
                with transaction.atomic():
                    # Validate only if new paid source is safe
                    if new_paid_source == 'safe':
                        if old_paid_source != 'safe':
                            # Full amount must now be covered by safe
                            SafeService.validate_sufficient_balance(branch_id, new_amount)
                        elif new_amount > old_amount:
                            # Only the delta must be available
                            SafeService.validate_sufficient_balance(branch_id, new_amount - old_amount)
                    else:
                        ExpenseValidationService.validate_expense_limit(branch_id, new_amount)

                    # Update expense
                    expense = serializer.save()

                    # Update safe transaction if necessary
                    if old_paid_source == 'safe' and new_paid_source != 'safe':
                        # Revert old expense from safe
                        SafeService.record_transaction(
                            branch=expense.branch,
                            amount=old_amount,
                            transaction_type='income',
                            reason=f"Revert: {expense.main_category.name} - {expense.sub_category.name}",
                            reference_id=f"expense-{expense.id}"
                        )
                    elif old_paid_source != 'safe' and new_paid_source == 'safe':
                        # New expense from safe
                        SafeService.record_transaction(
                            branch=expense.branch,
                            amount=new_amount,
                            transaction_type='expense',
                            reason=f"{expense.main_category.name} - {expense.sub_category.name}",
                            reference_id=f"expense-{expense.id}"
                        )
                    elif old_paid_source == 'safe' and new_paid_source == 'safe':
                        delta = new_amount - old_amount
                        if delta != 0:
                            txn_type = 'expense' if delta > 0 else 'income'
                            SafeService.record_transaction(
                                branch=expense.branch,
                                amount=abs(delta),
                                transaction_type=txn_type,
                                reason=f"Adjustment: {expense.main_category.name} - {expense.sub_category.name}",
                                reference_id=f"expense-{expense.id}"
                            )

                    return Response(ExpenseSerializer(expense).data, status=status.HTTP_200_OK)

            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ExpenseRetrieveView(generics.RetrieveAPIView):
    queryset = Expense.objects.all()
    serializer_class = ExpenseSerializer

