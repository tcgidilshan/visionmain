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
        
class ExpenseUpdateView(generics.UpdateAPIView):
    queryset = Expense.objects.all()
    serializer_class = ExpenseSerializer

    def update(self, request, *args, **kwargs):
        instance = self.get_object()

        # Capture the original amount
        original_amount = instance.amount
        original_date = instance.created_at.date()
        branch_id = instance.branch_id

        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        updated_amount = serializer.validated_data.get('amount', original_amount)

        # Calculate adjusted total: (current total - original + new)
        try:
            ExpenseValidationService.validate_expense_update(
                expense_instance=instance,
                new_amount=updated_amount,
                branch_id=branch_id,
                date=original_date
            )
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            self.perform_update(serializer)
        return Response(serializer.data, status=status.HTTP_200_OK)

