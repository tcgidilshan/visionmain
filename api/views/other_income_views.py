from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.filters import OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from ..models import OtherIncome, OtherIncomeCategory
from ..serializers import OtherIncomeSerializer, OtherIncomeCategorySerializer
from ..services.time_zone_convert_service import TimezoneConverterService
from rest_framework.views import APIView
from django.db.models import Sum

# -------------------------------
# 🔹 CATEGORY CRUD
# -------------------------------

class OtherIncomeCategoryListCreateView(generics.ListCreateAPIView):
    queryset = OtherIncomeCategory.objects.all()
    serializer_class = OtherIncomeCategorySerializer


class OtherIncomeCategoryRetrieveUpdateView(generics.RetrieveUpdateDestroyAPIView):
    queryset = OtherIncomeCategory.objects.all()
    serializer_class = OtherIncomeCategorySerializer


# -------------------------------
# 🔹 OTHER INCOME CRUD
# -------------------------------

class OtherIncomeListCreateView(generics.ListCreateAPIView):
    queryset = OtherIncome.objects.all()
    serializer_class = OtherIncomeSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['branch', 'category', 'date']  # ✅ filter by date/branch/category
    ordering_fields = ['date', 'amount']
    ordering = ['-date']  # default latest first

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Ensure timezone-aware datetime is set
        validated_data = serializer.validated_data
        validated_data['date'] = timezone.now()
        
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def get_queryset(self):
        """
        Add timezone-aware date filtering support
        """
        queryset = super().get_queryset()
        
        # Handle date filtering with timezone support
        start_date = self.request.query_params.get('start_date')
        # end_date = self.request.query_params.get('end_date')
        
        if start_date :
            start_datetime, end_datetime = TimezoneConverterService.format_date_with_timezone(
                start_date, None
            )
            print("start_datetime",start_datetime)
            if start_datetime and end_datetime:
                queryset = queryset.filter(date__range=(start_datetime, end_datetime))
        
        return queryset


class OtherIncomeRetrieveUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    queryset = OtherIncome.objects.all()
    serializer_class = OtherIncomeSerializer

class OtherIncomeReportView(APIView):
    def get(self, request):
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        branch_id = request.query_params.get('branch_id')

        if not start_date or not branch_id:
            return Response({
                "error": "start_date and branch_id are required."
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            start_datetime, end_datetime = TimezoneConverterService.format_date_with_timezone(start_date, end_date)
            
            queryset = OtherIncome.objects.select_related('category').filter(
                date__range=[start_datetime, end_datetime],
                branch_id=branch_id
            ).order_by('-date')

            total = queryset.aggregate(total_income=Sum('amount'))['total_income'] or 0

            return Response({
                "total_income": total,
                "other_incomes": OtherIncomeSerializer(queryset, many=True).data
            })

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)