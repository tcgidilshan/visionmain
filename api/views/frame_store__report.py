from rest_framework import generics, filters
from rest_framework.response import Response
from ..models import FrameStockHistory, FrameStock,OrderItem,Branch
from ..serializers import FrameStockHistorySerializer
from ..services.pagination_service import PaginationService
from django.db.models import Sum, Q, Min, Max
from datetime import datetime
from django.utils import timezone

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

class FrameSaleReportView(generics.ListAPIView):
    serializer_class = FrameStockHistorySerializer
    
    def get_queryset(self):
       
        # Get query parameters
        store_id = self.request.query_params.get('store_id')
        date_start = self.request.query_params.get('date_start')
        date_end = self.request.query_params.get('date_end')
        
        if not store_id:
            return FrameStock.objects.none()
            
        store_branch_id = store_id
            
        # Convert date strings to datetime objects with proper timezone handling
        try:
            # Parse dates as naive datetimes first
            start_date = datetime.strptime(date_start, '%Y-%m-%d')
            end_date = datetime.strptime(date_end, '%Y-%m-%d')
            
            # Make end_date include the entire day
            end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            # Make timezone aware if needed
            if timezone.is_naive(start_date):
                start_date = timezone.make_aware(start_date)
            if timezone.is_naive(end_date):
                end_date = timezone.make_aware(end_date)
                
            print(f"DEBUG: Parsed date range - Start: {start_date}, End: {end_date}")
                
        except (ValueError, TypeError) as e:
            print(f"ERROR: Invalid date format - {e}")
            return FrameStock.objects.none()
            
        # Get frame stock history up to the end date
        # Get all frame stock history up to the end date
        stock_history = FrameStockHistory.objects.filter(
            timestamp__lte=end_date
        )
        
        # First, get all frames that have stock in the specified store (qty >= 0)
        frame_ids_in_store = FrameStock.objects.filter(
            branch_id=store_branch_id,
            qty__gte=0  # Include frames with zero quantity
        ).values_list('frame_id', flat=True).distinct()
        
        print(f"\n=== DEBUG: Frames in store {store_branch_id} (qty >= 0): {list(frame_ids_in_store)}")
        
        # Get frame details for all frames in the store (including zero quantity)
        frame_details = FrameStock.objects.filter(
            branch_id=store_branch_id,
            frame_id__in=frame_ids_in_store
        ).select_related('frame__brand', 'frame__code', 'frame__color')
        
        # Calculate store stocks for these frames
        store_stocks = stock_history.filter(
            branch_id=store_branch_id,
            frame_id__in=frame_ids_in_store
        ).values('frame').annotate(
            qty=Sum('quantity_changed')
        )
        
        # Debug: Print frame details being processed
        print("\n=== DEBUG: Frame Details ===")
        print(f"Total frames with stock > 0 in store {store_branch_id}: {frame_details.count()}")
        for stock in frame_details:
            print(f"  - Frame ID: {stock.frame_id}, Qty: {stock.qty}, Branch: {stock.branch_id}")
        
        # Create a mapping of frame_id to frame details
        frame_details_dict = {}
        for stock in frame_details:
            if stock.frame_id not in frame_details_dict:  # Only keep the first occurrence
                frame_details_dict[stock.frame_id] = stock.frame
        
        print(f"DEBUG: Processed frame_details_dict: {list(frame_details_dict.keys())}")
        
        # Calculate stock levels for the store branch
        current_branch_stocks = stock_history.filter(
            branch_id=store_branch_id,
            frame_id__in=frame_details_dict.keys()  # Only include frames that exist in the store
        ).values('frame').annotate(
            current_branch_qty=Sum('quantity_changed')
        )
        current_branch_dict = {
            item['frame']: max(0, item['current_branch_qty'])  # Ensure non-negative
            for item in current_branch_stocks
        }
        print(f"DEBUG: current_branch_dict: {current_branch_dict}")
        
        # Calculate stock levels for all other branches
        other_branches_stocks = stock_history.filter(
            ~Q(branch_id=store_branch_id)
        ).values('frame').annotate(
            total_other_qty=Sum('quantity_changed')
        )
        
        # Get sold quantities for each frame per branch in the specified date range
        print(f"\n=== DEBUG: Fetching sold quantities from {start_date} to {end_date} for store: {store_branch_id}")
        
        # Debug: Print the exact query being executed
        print(f"DEBUG: Sales query date range: {start_date} to {end_date}")
        
        # Debug: Check if there are any OrderItems at all
        total_order_items = OrderItem.objects.filter(frame__isnull=False).count()
        print(f"DEBUG: Total OrderItems with frames: {total_order_items}")
        
        # Debug: Check if there are any OrderItems in the date range
        date_range_items = OrderItem.objects.filter(
            order__order_date__gte=start_date,
            order__order_date__lte=end_date,
            frame__isnull=False
        ).count()
        print(f"DEBUG: OrderItems in date range: {date_range_items}")
        
        # Debug: Print the actual date range of orders in the system
        date_range = OrderItem.objects.filter(
            frame__isnull=False
        ).aggregate(
            min_date=Min('order__order_date'),
            max_date=Max('order__order_date')
        )
        print(f"DEBUG: System order date range: {date_range['min_date']} to {date_range['max_date']}")
        
        # Debug: Check the actual query being executed
        print(f"DEBUG: Querying sales from {start_date} to {end_date}")
        
        # Use direct datetime comparison instead of __date__range to avoid timezone issues
        sold_quantities = OrderItem.objects.filter(
            order__order_date__gte=start_date,
            order__order_date__lte=end_date,
            frame__isnull=False,
            is_deleted=False,
            order__is_deleted=False,
            order__is_refund=False
        ).values('frame', 'order__branch').annotate(
            total_sold=Sum('quantity')
        )
        
        # Debug: Print the raw SQL query
        print(f"DEBUG: Raw SQL Query: {sold_quantities.query}")
        
        results = list(sold_quantities)
        print(f"DEBUG: Raw sold quantities query results: {results}")
        
        # Debug: Print sample order dates to verify the range
        if not results:
            print("\n=== DEBUG: No sales found in the specified date range. Checking for any sales data...")
            sample_sales = OrderItem.objects.filter(
                frame__isnull=False,
                is_deleted=False,
                order__is_deleted=False,
                order__is_refund=False
            ).select_related('order').order_by('-order__order_date')[:5]
            
            if sample_sales.exists():
                print("DEBUG: Sample of recent sales (most recent first):")
                for item in sample_sales:
                    print(f"  - Order {item.order.id} on {item.order.order_date}: "
                          f"Frame {item.frame_id}, Qty: {item.quantity}")
            else:
                print("DEBUG: No sales records found in the system at all.")
        
        # Convert to dictionary for faster lookup
        sold_quantities_dict = {}
        for item in sold_quantities:
            if item['total_sold']:
                frame_id = str(item['frame'])  # Ensure frame_id is string for consistent lookup
                branch_id = int(item['order__branch'])  # Convert branch_id to int for consistent comparison
                if frame_id not in sold_quantities_dict:
                    sold_quantities_dict[frame_id] = {}
                sold_quantities_dict[frame_id][branch_id] = item['total_sold']
        
        # Calculate other branches quantity
        other_branches_stocks = stock_history.filter(
            ~Q(branch_id=store_branch_id)
        ).values('frame').annotate(
            total_other_qty=Sum('quantity_changed')
        )
        
        other_branches_dict = {
            item['frame']: item['total_other_qty'] 
            for item in other_branches_stocks
        }
        
        print(f"DEBUG: Processed sold_quantities_dict: {sold_quantities_dict}")
        print(f"DEBUG: other_branches_dict: {other_branches_dict}")
        print(f"DEBUG: Total frames with sales: {len(sold_quantities_dict)}")
        
        # Debug: Print frame_ids we're processing
        frame_ids = list(frame_details_dict.keys())
        print(f"DEBUG: Processing {len(frame_ids)} frames. First 5 frame IDs: {frame_ids[:5]}")
        
        # Debug: Check if any frame has sales
        frames_with_sales = [fid for fid in frame_ids if str(fid) in sold_quantities_dict]
        print(f"DEBUG: Found {len(frames_with_sales)} frames with sales data")
        print(f"DEBUG: Frames with sales: {frames_with_sales}")
        
        # Get all branches and their stock for each frame
  
        
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
                    print(f"  - Found stock for frame {frame_id} in branch {branch_id}: {current_qty}")
                else:
                    print(f"  - No stock record found for frame {frame_id} in branch {branch_id}")
                    # Debug: Check if this frame exists in Frame model
                    from ..models import Frame
                    frame_exists = Frame.objects.filter(id=frame_id).exists()
                    print(f"    - Frame {frame_id} exists in Frame model: {frame_exists}")
                    
                    # Debug: Check all stock records for this frame
                    all_stock = FrameStock.objects.filter(frame_id=frame_id).values('branch_id', 'qty')
                    print(f"    - All stock records for frame {frame_id}: {list(all_stock)}")
                    
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
                'sold_count': sum(sold_quantities_dict.get(str(frame_id), {}).values()) if str(frame_id) in sold_quantities_dict else 0,
                'debug_sold_data': sold_quantities_dict.get(str(frame_id), "No sales data"),
                'as_of_date': end_date.date().isoformat(),
                'branches': frame_branches  # Includes branch_id, branch_name, qty, and received_from_store
            })
            
        return result
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        return Response(queryset)