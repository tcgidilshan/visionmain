from rest_framework import generics, filters
from rest_framework.response import Response
from django.db import models
from ..models import FrameStockHistory, Frame
from ..serializers import FrameStockHistorySerializer
from ..services.pagination_service import PaginationService

class FrameHistoryReportView(generics.ListAPIView):
    pagination_class = PaginationService
    serializer_class = FrameStockHistorySerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['frame__id', 'branch__id']  # Allow searching by frame ID and branch ID

    def get_queryset(self):
        # Optimize queries by selecting related objects
        queryset = FrameStockHistory.objects.select_related(
            'frame__brand',
            'frame__code',
            'frame__color',
            'branch',
            'transfer_to'
        ).all()
        
        # Get query parameters
        frame_id = self.request.query_params.get('frame_id')
        branch_id = self.request.query_params.get('branch_id')
        action = self.request.query_params.get('action')  # Optional: filter by specific action
        
        # Apply filters if parameters are provided
        if frame_id:
            queryset = queryset.filter(frame_id=frame_id)
        
        if branch_id:
            # Include records where branch is either source (branch_id) or destination (transfer_to_id)
            queryset = queryset.filter(
                models.Q(branch_id=branch_id) | 
                models.Q(transfer_to_id=branch_id)
            )
            
        if action:
            queryset = queryset.filter(action=action.lower())
            
        # Order by most recent first
        return queryset.order_by('-timestamp').only(
            'id',
            'frame__id',
            'frame__brand__name',
            'frame__code__name',
            'frame__color__name',
            'frame__size',
            'frame__species',
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

class FrameSaleReportView(generics.ListAPIView):
    serializer_class = FrameStockHistorySerializer
    
    def get_queryset(self):
        from django.db.models import Sum, Q, F
        from ..models import Frame, FrameStock
        
        # Get query parameters
        store_branch_id = self.request.query_params.get('store_branch_id')
        date_start = self.request.query_params.get('date_start')
        date_end = self.request.query_params.get('date_end')
        branch_id = self.request.query_params.get('branch_id')
        
        if not all([store_branch_id, branch_id, date_start, date_end]):
            return FrameStock.objects.none()
            
        # Get all frames with their quantities in the specified store branch
        store_stocks = FrameStock.objects.filter(
            branch_id=store_branch_id
        ).select_related('frame__brand', 'frame__code', 'frame__color')
        
        # Get total quantities from all other branches
        other_branches_stocks = FrameStock.objects.filter(
            ~Q(branch_id=store_branch_id)
        ).values('frame').annotate(
            total_other_qty=Sum('qty')
        )
        
        # Convert to dictionary for faster lookup
        other_branches_dict = {
            item['frame']: item['total_other_qty'] 
            for item in other_branches_stocks
        }
        
        # Prepare the result
        result = []
        for stock in store_stocks:
            frame = stock.frame
            result.append({
                'frame_id': frame.id,
                'brand': frame.brand.name,
                'code': frame.code.name,
                'color': frame.color.name,
                'size': frame.size,
                'species': frame.species,
                'store_branch_qty': stock.qty,
                'other_branches_qty': other_branches_dict.get(frame.id, 0),
                'total_qty': stock.qty + other_branches_dict.get(frame.id, 0)
            })
            
        return result
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        return Response(queryset)  # Allow searching by frame ID and branch ID
