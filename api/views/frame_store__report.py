from rest_framework import generics, filters
from rest_framework.response import Response
from django.db import models
from ..models import FrameStockHistory, FrameStock
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
        
        if not all([store_branch_id, date_start, date_end]):
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
        
        # Calculate stock levels for the store branch
        current_branch_stocks = stock_history.filter(
            branch_id=store_branch_id
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
        
        # Get sold quantities for each frame per branch in the specified date range
        sold_quantities = OrderItem.objects.filter(
            order__order_date__date__range=(start_date, end_date),
            frame__isnull=False,
            is_deleted=False,
            order__is_deleted=False,
            order__is_refund=False
        ).values('frame', 'order__branch').annotate(
            total_sold=Sum('quantity')
        )
        
        # Convert to dictionary for faster lookup
        other_branches_dict = {
            item['frame']: item['total_other_qty'] 
            for item in other_branches_stocks
        }
        
        # Create a dictionary to store sold quantities per frame and branch
        sold_quantities_dict = {}
        for item in sold_quantities:
            if item['total_sold']:
                frame_id = str(item['frame'])  # Ensure frame_id is string for consistent lookup
                branch_id = int(item['order__branch'])  # Convert branch_id to int for consistent comparison
                if frame_id not in sold_quantities_dict:
                    sold_quantities_dict[frame_id] = {}
                sold_quantities_dict[frame_id][branch_id] = item['total_sold']
        
        # Get all branches and their stock for each frame
        from ..models import Branch
        
        # Get all branches except the store branch
        all_branches = Branch.objects.exclude(id=store_branch_id)
        
        # Get stock quantities for each branch for each frame
        branch_stocks = {}
        # Get transfer counts from store branch to each branch for each frame
        branch_transfers = {}
        
        for branch in all_branches:
            # Current stock in branch
            branch_stock = stock_history.filter(
                branch_id=branch.id
            ).values('frame').annotate(
                qty=Sum('quantity_changed')
            )
            
            # Count of frames received from store branch
            received_from_store = FrameStockHistory.objects.filter(
                branch_id=store_branch_id,
                transfer_to=branch,
                action='transfer',
                timestamp__lte=end_date
            ).values('frame').annotate(
                received_count=Sum('quantity_changed')
            )
            
            # Store the received counts
            for item in received_from_store:
                frame_id = item['frame']
                if frame_id not in branch_transfers:
                    branch_transfers[frame_id] = []
                branch_transfers[frame_id].append({
                    'branch_id': branch.id,
                    'branch_name': branch.branch_name,
                    'received_from_store': item['received_count'] or 0
                })
            
            # Store the current stock
            for item in branch_stock:
                frame_id = item['frame']
                if frame_id not in branch_stocks:
                    branch_stocks[frame_id] = []
                branch_stocks[frame_id].append({
                    'branch_id': branch.id,
                    'branch_name': branch.branch_name,
                    'qty': max(0, item['qty'])  # Ensure non-negative
                })
        
        # Prepare the result
        result = []
        for stock in store_stocks:
            frame_id = stock['frame']
            frame = frame_details_dict.get(frame_id)
            if not frame:
                continue
                
            qty = max(0, stock['qty'])  # Ensure non-negative
            other_qty = max(0, other_branches_dict.get(frame_id, 0))
            
            # Get current stock from FrameStock for all branches for this fram
            frame_branches = []
            
            # Get all branches that have this frame in stock
            current_stocks = FrameStock.objects.filter(
                frame_id=frame_id
            ).select_related('branch')
            
            # Get all branches that received this frame from store (even if they have no current stock)
            all_relevant_branches = set()
            
            # Add branches that have current stock
            for stock in current_stocks:
                all_relevant_branches.add((stock.branch.id, stock.branch.branch_name))
            
            # Add branches that received frames from store (even if they have no current stock)
            if frame_id in branch_transfers:
                for transfer in branch_transfers[frame_id]:
                    all_relevant_branches.add((transfer['branch_id'], transfer['branch_name']))
            
            # Create the branches array with complete information
            for branch_id, branch_name in all_relevant_branches:
                # Get current stock for this branch
                current_qty = 0
                current_stock = FrameStock.objects.filter(
                    frame_id=frame_id,
                    branch_id=branch_id
                ).first()
                
                if current_stock:
                    current_qty = current_stock.qty
                
                # Initialize branch data with current stock and sold quantity
                branch_data = {
                    'branch_id': branch_id,
                    'branch_name': branch_name,
                    'stock_count': max(0, current_qty),  # Current stock count in the branch
                    'stock_received': 0,  # Total received from store
                    'sold_qty': sold_quantities_dict.get(str(frame_id), {}).get(int(branch_id), 0),  # Sold in date range
                }
                
                # Update with received from store count if exists
                if frame_id in branch_transfers:
                    for transfer in branch_transfers[frame_id]:
                        if transfer['branch_id'] == branch_id:
                            received_qty = transfer['received_from_store']
                            branch_data['stock_received'] = received_qty
                            break
                
                frame_branches.append(branch_data)
            
            result.append({
                'frame_id': frame_id,
                'brand': frame.brand.name,
                'code': frame.code.name,
                'color': frame.color.name,
                'size': frame.size,
                'species': frame.species,
                'store_branch_qty': qty,
                'store_branch_qty': current_branch_dict.get(frame_id, 0),
                'other_branches_qty': other_qty,
                'total_qty': qty + other_qty,
                'sold_count': sold_quantities_dict.get(frame_id, 0),
                'as_of_date': end_date.date().isoformat(),
                'branches': frame_branches  # Includes branch_id, branch_name, qty, and received_from_store
            })
            
        return result
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        return Response(queryset)