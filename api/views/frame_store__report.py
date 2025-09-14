from rest_framework import generics, filters
from rest_framework.response import Response
from ..models import FrameStockHistory, FrameStock,OrderItem,Branch,Frame
from ..serializers import FrameStockHistorySerializer
from ..services.pagination_service import PaginationService
from django.db.models import Sum, Q, Min, Max
from datetime import datetime
from django.utils import timezone
from django.conf import settings
from rest_framework.views import APIView
from ..services.time_zone_convert_service import TimezoneConverterService
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
                Q(branch_id=branch_id) | 
                Q(transfer_to_id=branch_id)
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

class FrameSaleReportView(APIView):
    def get(self, request, *args, **kwargs):
        store_branch_id = request.query_params.get('store_branch_id')
        date_start = request.query_params.get('date_start')
        date_end = request.query_params.get('date_end')
        if not store_branch_id:
            return Response({'error': 'store_branch_id is missing'}, status=400)

        start_datetime, end_datetime = TimezoneConverterService.format_date_with_timezone(date_start, date_end)
        if not start_datetime or not end_datetime:
            return Response({'error': 'Invalid date format'}, status=400)

        # Get all frames for this branch (only the ones initialized in this branch)
        frames = Frame.objects.filter(initial_branch_id=store_branch_id).select_related(
            'brand', 'code', 'color'
        )
        frame_ids = [frame.id for frame in frames]
        
        # Create lookup dictionaries for quick access
        frame_dict = {frame.id: frame for frame in frames}
        
        # Get all branches
        all_branches = Branch.objects.all()
        branch_dict = {branch.id: branch for branch in all_branches}
        
        # Get current stock levels for these frames from FrameStock
        current_stocks = FrameStock.objects.filter(
            frame_id__in=frame_ids
        ).values('frame_id', 'branch_id', 'qty')
        
        # Group stocks by frame_id and branch_id
        stock_by_frame_branch = {}
        for stock in current_stocks:
            frame_id = stock['frame_id']
            branch_id = stock['branch_id']
            qty = stock['qty']
            
            if frame_id not in stock_by_frame_branch:
                stock_by_frame_branch[frame_id] = {}
                
            stock_by_frame_branch[frame_id][branch_id] = qty
        
        # Get total stock by frame
        total_stock_by_frame = {}
        store_stock_by_frame = {}
        other_stock_by_frame = {}
        
        for frame_id, branch_stocks in stock_by_frame_branch.items():
            total = sum(branch_stocks.values())
            store_qty = branch_stocks.get(int(store_branch_id), 0)
            other_qty = total - store_qty
            
            total_stock_by_frame[frame_id] = total
            store_stock_by_frame[frame_id] = store_qty
            other_stock_by_frame[frame_id] = other_qty
        
        # Get sold quantities within date range by branch
        sold_items = OrderItem.objects.filter(
            frame_id__in=frame_ids,
            is_deleted=False,
            created_at__gte=start_datetime,
            created_at__lte=end_datetime
        ).values('frame_id', 'order__branch_id').annotate(sold_count=Sum('quantity'))
        
        # Group sold quantities by frame_id and branch_id
        sold_by_frame_branch = {}
        for item in sold_items:
            frame_id = item['frame_id']
            branch_id = item['order__branch_id']
            count = item['sold_count'] or 0
            
            if frame_id not in sold_by_frame_branch:
                sold_by_frame_branch[frame_id] = {}
                
            sold_by_frame_branch[frame_id][branch_id] = count
        
        # Calculate total sold by frame
        sold_by_frame = {}
        for frame_id, branch_sales in sold_by_frame_branch.items():
            sold_by_frame[frame_id] = sum(branch_sales.values())
        
        # Get received stock (transfers to branch from store)
        received_stock = FrameStockHistory.objects.filter(
            frame_id__in=frame_ids,
            branch_id=store_branch_id,
            action='transfer',
            timestamp__gte=start_datetime,
            timestamp__lte=end_datetime
        ).values('frame_id', 'transfer_to_id').annotate(received_count=Sum('quantity_changed'))
        
        # Group received stock by frame_id and branch_id
        received_by_frame_branch = {}
        for item in received_stock:
            frame_id = item['frame_id']
            branch_id = item['transfer_to_id']
            count = item['received_count'] or 0
            
            if frame_id not in received_by_frame_branch:
                received_by_frame_branch[frame_id] = {}
                
            received_by_frame_branch[frame_id][branch_id] = count
        
        # Get removed stock (removals from any branch)
        removed_stock = FrameStockHistory.objects.filter(
            frame_id__in=frame_ids,
            action='remove',
            timestamp__gte=start_datetime,
            timestamp__lte=end_datetime
        ).values('frame_id', 'branch_id').annotate(removed_count=Sum('quantity_changed'))
        
        # Group removed stock by frame_id and branch_id
        removed_by_frame_branch = {}
        for item in removed_stock:
            frame_id = item['frame_id']
            branch_id = item['branch_id']
            count = abs(item['removed_count'] or 0)  # Make sure it's positive
            
            if frame_id not in removed_by_frame_branch:
                removed_by_frame_branch[frame_id] = {}
                
            removed_by_frame_branch[frame_id][branch_id] = count
        
        # Build the result
        result = []
        for frame_id in frame_ids:
            frame = frame_dict.get(frame_id)
            if not frame:
                continue
                
            # Get branch data for this frame - include ALL branches
            branches_data = []
            
            for branch in all_branches:
                branch_id = branch.id
                
                # Always include each branch, regardless of activity
                branch_data = {
                    'branch_id': branch_id,
                    'branch_name': branch.branch_name,
                    'stock_count': stock_by_frame_branch.get(frame_id, {}).get(branch_id, 0),
                    'stock_received': received_by_frame_branch.get(frame_id, {}).get(branch_id, 0),
                    'stock_removed': removed_by_frame_branch.get(frame_id, {}).get(branch_id, 0),
                    'sold_qty': sold_by_frame_branch.get(frame_id, {}).get(branch_id, 0) or 0
                }
                
                branches_data.append(branch_data)
            
            # Calculate stock values
            store_branch_qty = store_stock_by_frame.get(frame_id, 0)
            other_branches_qty = other_stock_by_frame.get(frame_id, 0)
            total_qty = total_stock_by_frame.get(frame_id, 0)
            
            result.append({
                'frame_id': frame_id,
                'brand': frame.brand.name,
                'code': frame.code.name,
                'color': frame.color.name,
                'size': frame.size,
                'species': frame.species,
                'store_branch_qty': store_branch_qty,
                'other_branches_qty': other_branches_qty,
                'total_qty': total_qty,
                'total_available': total_qty,  # Added this field as requested
                'sold_count': sold_by_frame.get(frame_id, 0),
                'current_branch_qty': store_branch_qty,  # Same as store_branch_qty
                'as_of_date': end_datetime.date().isoformat(),
                'branches': branches_data
            })
        
        return Response(result, status=200)