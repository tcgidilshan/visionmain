from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.filters import OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from ..models import OtherIncome, OtherIncomeCategory
from ..serializers import OtherIncomeSerializer, OtherIncomeCategorySerializer

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
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class OtherIncomeRetrieveUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    queryset = OtherIncome.objects.all()
    serializer_class = OtherIncomeSerializer
