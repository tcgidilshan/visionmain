from rest_framework import generics, filters
from rest_framework.response import Response
from ..models import FrameStockHistory, FrameStock,OrderItem,Branch
from ..serializers import FrameStockHistorySerializer
from ..services.pagination_service import PaginationService
from django.db.models import Sum, Q, Min, Max
from datetime import datetime
from django.utils import timezone
class LensSaleReportView(generics.ListAPIView):
  def get_queryset(self):
    
    return LensStockHistory.objects.all()