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
        from django.db.models import Sum, Q, F, Count
        from datetime import datetime
        from django.utils import timezone
        from ..models import Frame, FrameStock, Order, OrderItem
        
        # Get query parameters
        store_branch_id = self.request.query_params.get('store_branch_id')
        date_start = self.request.query_params.get('date_start')
        date_end = self.request.query_params.get('date_end')
        branch_id = self.request.query_params.get('branch_id')
        
        if not all([store_branch_id, branch_id, date_start, date_end]):
            return FrameStock.objects.none()
            
        # Convert date strings to datetime objects
        try:
            start_date = datetime.strptime(date_start, '%Y-%m-%d').date()
            end_date = datetime.strptime(date_end, '%Y-%m-%d').date()
            # Add time to end_date to include the entire day
            end_date = timezone.make_aware(datetime.combine(end_date, datetime.max.time()))
        except (ValueError, TypeError):
            return FrameStock.objects.none()
            
        # Get frame stock history up to the end date
        from ..models import FrameStockHistory
        
        # Get all frame stock history up to the end date
        stock_history = FrameStockHistory.objects.filter(
            timestamp__lte=end_date
        )
        
        # Calculate stock levels as of the end date for the store branch
        store_stocks = stock_history.filter(
            branch_id=store_branch_id
        ).values('frame').annotate(
            qty=Sum('quantity_changed')
        )
        
        # Get frame details for the store branch
        frame_details = FrameStock.objects.filter(
            branch_id=store_branch_id
        ).select_related('frame__brand', 'frame__code', 'frame__color')
        
        # Create a mapping of frame_id to frame details
        frame_details_dict = {stock.frame.id: stock.frame for stock in frame_details}
        
        # Calculate stock levels for the current branch
        current_branch_stocks = stock_history.filter(
            branch_id=branch_id
        ).values('frame').annotate(
            current_branch_qty=Sum('quantity_changed')
        )
        current_branch_dict = {
            item['frame']: max(0, item['current_branch_qty'])  # Ensure non-negative
            for item in current_branch_stocks
        }
        
        # Calculate stock levels for all other branches
        other_branches_stocks = stock_history.filter(
            ~Q(branch_id=store_branch_id)
        ).values('frame').annotate(
            total_other_qty=Sum('quantity_changed')
        )
        
        # Get sold quantities for each frame in the specified date range and branch
        sold_quantities = OrderItem.objects.filter(
            order__branch_id=branch_id,
            order__order_date__date__range=(start_date, end_date),
            frame__isnull=False,
            is_deleted=False,
            order__is_deleted=False,
            order__is_refund=False
        ).values('frame').annotate(
            total_sold=Sum('quantity')
        )
        
        # Convert to dictionary for faster lookup
        other_branches_dict = {
            item['frame']: item['total_other_qty'] 
            for item in other_branches_stocks
        }
        
        sold_quantities_dict = {
            item['frame']: item['total_sold'] 
            for item in sold_quantities if item['total_sold']
        }
        
        # Prepare the result
        result = []
        for stock in store_stocks:
            frame_id = stock['frame']
            frame = frame_details_dict.get(frame_id)
            if not frame:
                continue
                
            qty = max(0, stock['qty'])  # Ensure non-negative
            other_qty = max(0, other_branches_dict.get(frame_id, 0))
            
            result.append({
                'frame_id': frame_id,
                'brand': frame.brand.name,
                'code': frame.code.name,
                'color': frame.color.name,
                'size': frame.size,
                'species': frame.species,
                'store_branch_qty': qty,
                'current_branch_qty': current_branch_dict.get(frame_id, 0),
                'other_branches_qty': other_qty,
                'total_qty': qty + other_qty,
                'sold_count': sold_quantities_dict.get(frame_id, 0),
                'as_of_date': end_date.date().isoformat()
            })
            
        return result
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        return Response(queryset)
git