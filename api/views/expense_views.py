# views.py

from rest_framework import generics,status
from ..models import ExpenseMainCategory, ExpenseSubCategory,Expense,ExpenseReturn
from ..serializers import ExpenseMainCategorySerializer, ExpenseSubCategorySerializer,ExpenseSerializer,ExpenseReportSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from ..services.expense_validation_service import ExpenseValidationService
from ..services.safe_service import SafeService
from django.db.models import Sum
from django.utils.dateparse import parse_date
from django.db import transaction
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from decimal import Decimal
from ..services.time_zone_convert_service import TimezoneConverterService
from django.utils import timezone
from ..services.pagination_service import PaginationService

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
                # Validate safe balance if paid from safe
                if paid_source == "safe":
                    SafeService.validate_sufficient_balance(branch_id, amount)
                else:
                    ExpenseValidationService.validate_expense_limit(branch_id, amount)

                expense = serializer.save()

                # Record safe transaction if needed
                if paid_source == "safe":
                    SafeService.record_transaction(
                        branch=expense.branch,
                        expense=expense,
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

        if not start_date or not branch_id:
            return Response({
                "error": "start_date, end_date, and branch_id are required."
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            start_datetime, end_datetime = TimezoneConverterService.format_date_with_timezone(start_date, end_date)
            
            queryset = Expense.objects.select_related('main_category', 'sub_category').filter(
                created_at__range=[start_datetime, end_datetime],
                branch_id=branch_id
            ).order_by('-created_at')

            total = queryset.aggregate(total_expense=Sum('amount'))['total_expense'] or 0
           

            cash_total = queryset.filter(paid_source='cash').aggregate(cash_total=Sum('amount'))['cash_total'] or 0
           


            safe_total = queryset.filter(paid_source='safe').aggregate(safe_total=Sum('amount'))['safe_total'] or 0
           

            bank_total = queryset.filter(paid_source='bank').aggregate(bank_total=Sum('amount'))['bank_total'] or 0
           

       
            return Response({
                "total_expense": total,
                "cash_expense_total": cash_total,
                "safe_expense_total": safe_total,
                "bank_expense_total": bank_total,
                "subtotal_expense": total,
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
                        ExpenseValidationService.validate_expense_update_limit(branch_id, new_amount, old_amount)

                    # Update expense
                    expense = serializer.save()

                    # Update safe transaction if necessary
                    if old_paid_source == 'safe' and new_paid_source != 'safe':
                        # Revert old expense from safe
                        SafeService.record_transaction(
                            branch=expense.branch,
                            expense=expense,
                            amount=old_amount,
                            transaction_type='income',
                            reason=f"Revert: {expense.main_category.name} - {expense.sub_category.name}",
                            reference_id=f"expense-{expense.id}"
                        )
                    elif old_paid_source != 'safe' and new_paid_source == 'safe':
                        # New expense from safe
                        SafeService.record_transaction(
                            branch=expense.branch,
                              expense=expense,
                            amount=new_amount,
                          
                            transaction_type='expense',
                            reason=f"{expense.main_category.name} - {expense.sub_category.name}",
                            reference_id=f"expense-{expense.id}"
                        )
                    elif old_paid_source == 'safe' and new_paid_source == 'safe':
                        # Update existing safe transaction with new amount
                        SafeService.record_transaction(
                            branch=expense.branch,
                            expense=expense,
                            amount=new_amount,
                            transaction_type='expense',
                            reason=f"{expense.main_category.name} - {expense.sub_category.name}",
                            reference_id=f"expense-{expense.id}"
                        )

                    return Response(ExpenseSerializer(expense).data, status=status.HTTP_200_OK)

            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ExpenseRetrieveView(generics.RetrieveAPIView):
    queryset = Expense.objects.all()
    serializer_class = ExpenseSerializer

class ExpenceSummeryReportView(APIView):

    
    def get(self, request):
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        branch_id = request.query_params.get('branch_id')

        if not start_date or not end_date or not branch_id:
            return Response({
                "error": "start_date, end_date, and branch_id are required."
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            start_datetime, end_datetime = TimezoneConverterService.format_date_with_timezone(start_date, end_date)
            
            # Get expenses grouped by subcategory
            expense_queryset = Expense.objects.filter(
                created_at__range=[start_datetime, end_datetime],
                branch_id=branch_id
            ).values(
                'main_category__name',
                'sub_category__name',
                'sub_category_id'
            ).annotate(
                total=Sum('amount')
            ).order_by('main_category__name', 'sub_category__name')
            
            # Get expense returns grouped by subcategory
            return_queryset = ExpenseReturn.objects.filter(
                created_at__range=[start_datetime, end_datetime],
                branch_id=branch_id
            ).values(
                'main_category__name',
                'sub_category__name',
                'sub_category_id'
            ).annotate(
                total=Sum('amount')
            ).order_by('main_category__name', 'sub_category__name')
            
            # Convert to dictionaries for easier manipulation
            expense_dict = {item['sub_category_id']: item for item in expense_queryset}
            return_dict = {item['sub_category_id']: item for item in return_queryset}
            
            # Combine results and calculate net amounts
            combined_results = []
            
            # Process all subcategory IDs from both datasets
            all_subcategory_ids = set(expense_dict.keys()) | set(return_dict.keys())
            
            for sub_cat_id in all_subcategory_ids:
                expense_data = expense_dict.get(sub_cat_id, {})
                return_data = return_dict.get(sub_cat_id, {})
                
                expense_amount = expense_data.get('total', 0)
                return_amount = return_data.get('total', 0)
                net_amount = expense_amount - return_amount
                
                # Use data from whichever source has it
                main_category = expense_data.get('main_category__name') or return_data.get('main_category__name')
                sub_category = expense_data.get('sub_category__name') or return_data.get('sub_category__name')
                
                combined_results.append({
                    'main_category': main_category,
                    'sub_category': sub_category,
                    'expense_amount': expense_amount,
                    'return_amount': return_amount,
                    'net_amount': net_amount
                })
            
            # Calculate totals
            total_expense = sum(item['expense_amount'] for item in combined_results)
            total_return = sum(item['return_amount'] for item in combined_results)
            net_total = total_expense - total_return
            
            return Response({
                "total_expense": total_expense,
                "total_return": total_return,
                "net_total": net_total,
                "summary_by_subcategory": combined_results
            })
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)