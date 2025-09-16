import datetime
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from ..models import Expense
from ..serializers import ExpenseReturnSerializer
from django.db.models import Q
from ..models import  ExpenseSubCategory,ExpenseReturn
from ..services.time_zone_convert_service import TimezoneConverterService

class ExpenceReturnAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ExpenseReturnSerializer(data=request.data)
        if serializer.is_valid():
            # Validate main_category and sub_category relationship
            main_category_id = serializer.validated_data.get('main_category').id
            sub_category_id = serializer.validated_data.get('sub_category').id
            
            # Check if sub_category belongs to main_category
            sub_category = ExpenseSubCategory.objects.filter(
                id=sub_category_id, 
                main_category_id=main_category_id
            ).first()
            
            if not sub_category:
                return Response(
                    {"error": "Sub category does not belong to the selected main category"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Ensure paid_from_safe is True if paid_source is 'safe'
            if serializer.validated_data.get('paid_source') == 'safe' and not serializer.validated_data.get('paid_from_safe'):
                serializer.validated_data['paid_from_safe'] = True
            
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def get(self, request, pk=None):
        if pk:
            try:
                expense_return = ExpenseReturn.objects.get(pk=pk)
            except ExpenseReturn.DoesNotExist:
                return Response(
                    {"error": f"ExpenseReturn with ID {pk} not found"},
                    status=status.HTTP_404_NOT_FOUND
                )
            serializer = ExpenseReturnSerializer(expense_return)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            # Extract query parameters
            start_date = request.query_params.get('start_date')
            end_date = request.query_params.get('end_date')
            branch_id = request.query_params.get('branch_id')

            # Use the timezone converter service
            start_datetime, end_datetime = TimezoneConverterService.format_date_with_timezone(start_date, end_date)
            print(f"Converted datetimes: {start_datetime}, {end_datetime}")

            queryset = ExpenseReturn.objects.all()  # <-- FIXED

            if start_datetime and end_datetime:
                queryset = queryset.filter(created_at__gte=start_datetime, created_at__lte=end_datetime)
            elif start_datetime:
                queryset = queryset.filter(created_at__gte=start_datetime)
            elif end_datetime:
                queryset = queryset.filter(created_at__lte=end_datetime)

            if branch_id:
                queryset = queryset.filter(branch_id=branch_id)

            serializer = ExpenseReturnSerializer(queryset, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
    
    def put(self, request, pk):
        try:
            expense_return = ExpenseReturn.objects.get(pk=pk)
        except ExpenseReturn.DoesNotExist:
            return Response(
                {"error": f"ExpenseReturn with ID {pk} not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Validation: Only allow update if created_at date is today
        now_date = datetime.datetime.now().date()
        created_date = expense_return.created_at.date()
        if created_date != now_date:
            return Response(
                {"error": "You can only edit records created today."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = ExpenseReturnSerializer(expense_return, data=request.data, partial=True)
        if serializer.is_valid():
            # Validate main_category and sub_category relationship if both are in the request
            main_category = serializer.validated_data.get('main_category')
            sub_category = serializer.validated_data.get('sub_category')
            
            if main_category and sub_category:
                sub_category_exists = ExpenseSubCategory.objects.filter(
                    id=sub_category.id, 
                    main_category_id=main_category.id
                ).exists()
                if not sub_category_exists:
                    return Response(
                        {"error": "Sub category does not belong to the selected main category"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Ensure paid_from_safe is True if paid_source is 'safe'
            if serializer.validated_data.get('paid_source') == 'safe':
                serializer.validated_data['paid_from_safe'] = True
            # Ensure paid_from_safe is False if paid_source is 'cash'
            if serializer.validated_data.get('paid_source') == 'cash':
                serializer.validated_data['paid_from_safe'] = False
            
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
