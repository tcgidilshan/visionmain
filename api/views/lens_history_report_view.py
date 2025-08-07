from rest_framework import generics,filters
from ..services.pagination_service import PaginationService
from ..models import LensStockHistory
from ..serializers import LensStockHistorySerializer
from django.db.models import Q
from rest_framework.response import Response



class LensHistoryReportView(generics.ListAPIView):
    pagination_class = PaginationService
    serializer_class = LensStockHistorySerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['lens__id', 'branch__id']  # Allow searching by frame ID and branch ID
    
    def get_queryset(self):
        queryset = LensStockHistory.objects.select_related(
            'lens__brand',
            'lens__coating',
            'lens__type',
            'branch',
            'transfer_to'
        ).all()
        lens_id = self.request.query_params.get('lens_id')
        branch_id = self.request.query_params.get('branch_id')
        action = self.request.query_params.get('action')  # Optional: filter by specific action
        
        # Apply filters if parameters are provided
        if lens_id:
            queryset = queryset.filter(lens_id=lens_id)
        
        if branch_id:
            # Include records where branch is either source (branch_id) or destination (transfer_to_id)
            queryset = queryset.filter(
                Q(branch_id=branch_id) | 
                Q(transfer_to_id=branch_id)
            )
            
        if action:
            queryset = queryset.filter(action=action.lower())
            
        # Order by most recent first
        return  queryset.order_by('-timestamp').only(
            'id',
            'lens__id',
            'lens__brand__name',
            'lens__coating__name',
            'lens__type__name',
            'action',
            'quantity_changed',
            'timestamp',
            'branch__id',
            'branch__branch_name',
            'branch__location',
            'transfer_to__id',
            'transfer_to__branch_name',
            'transfer_to__location'
        )
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
            
        # Paginate the queryset
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
            
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)