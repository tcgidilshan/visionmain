from rest_framework import generics, filters
from rest_framework.response import Response
from django.db.models import Sum, Q, F, Count
from datetime import datetime
from django.utils import timezone

from ..models import LensStockHistory, LensStock, OrderItem, Branch, Lens, LenseType, Coating, Brand, LensPower
from ..serializers import LensStockHistorySerializer
from ..services.pagination_service import PaginationService

class LensHistoryReportView(generics.ListAPIView):
    pagination_class = PaginationService
    serializer_class = LensStockHistorySerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['lens__id', 'branch__id']  # Allow searching by lens ID and branch ID

    def get_queryset(self):
        # Optimize queries by selecting related objects
        queryset = LensStockHistory.objects.select_related(
            'lens__type',
            'lens__coating',
            'lens__brand',
            'branch',
            'transfer_to'
        ).all()
        
        # Get query parameters
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
        return queryset.order_by('-timestamp')

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        
        # Paginate the queryset
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

class LensSaleReportView(generics.ListAPIView):
    serializer_class = LensStockHistorySerializer
    
    def get_queryset(self):
        # Get query parameters
        store_id = self.request.query_params.get('store_id')
        date_start = self.request.query_params.get('date_start')
        date_end = self.request.query_params.get('date_end')
        
        if not store_id:
            return LensStock.objects.none()
            
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
            return LensStock.objects.none()
            
        # Get lens stock history up to the end date
        stock_history = LensStockHistory.objects.filter(
            timestamp__lte=end_date
        )
        
        # First, get all lenses that have stock in the specified store (qty >= 0)
        lens_ids_in_store = LensStock.objects.filter(
            branch_id=store_branch_id,
            qty__gte=0  # Include lenses with zero quantity
        ).values_list('lens_id', flat=True).distinct()
        
        print(f"\n=== DEBUG: Lenses in store {store_branch_id} (qty >= 0): {list(lens_ids_in_store)}")
        
        # Get lens details for all lenses in the store (including zero quantity)
        lens_details = LensStock.objects.filter(
            branch_id=store_branch_id,
            lens_id__in=lens_ids_in_store
        ).select_related('lens__type', 'lens__coating', 'lens__brand')
        
        # Calculate store stocks for these lenses
        store_stocks = stock_history.filter(
            branch_id=store_branch_id,
            lens_id__in=lens_ids_in_store
        ).values('lens').annotate(
            qty=Sum('quantity_changed')
        )
        
        # Debug: Print lens details being processed
        print("\n=== DEBUG: Lens Details ===")
        print(f"Total lenses with stock > 0 in store {store_branch_id}: {lens_details.count()}")
        for stock in lens_details:
            print(f"  - Lens ID: {stock.lens_id}, Qty: {stock.qty}, Branch: {stock.branch_id}")
        
        # Create a mapping of lens_id to lens details
        lens_details_dict = {}
        for stock in lens_details:
            if stock.lens_id not in lens_details_dict:  # Only keep the first occurrence
                lens_details_dict[stock.lens_id] = stock.lens
        
        print(f"DEBUG: Processed lens_details_dict: {list(lens_details_dict.keys())}")
        
        # Calculate stock levels for the store branch
        current_branch_stocks = stock_history.filter(
            branch_id=store_branch_id,
            lens_id__in=lens_details_dict.keys()  # Only include lenses that exist in the store
        ).values('lens').annotate(
            current_branch_qty=Sum('quantity_changed')
        )
        current_branch_dict = {
            item['lens']: max(0, item['current_branch_qty'])  # Ensure non-negative
            for item in current_branch_stocks
        }
        print(f"DEBUG: current_branch_dict: {current_branch_dict}")
        
        # Calculate stock levels for all other branches
        other_branches_stocks = stock_history.filter(
            ~Q(branch_id=store_branch_id)
        ).values('lens').annotate(
            total_other_qty=Sum('quantity_changed')
        )
        
        # Convert to dictionary for faster lookup
        other_branches_dict = {
            item['lens']: max(0, item['total_other_qty'])  # Ensure non-negative
            for item in other_branches_stocks
        }
        
        # Get sold quantities for each lens per branch in the specified date range
        print(f"\n=== DEBUG: Fetching sold quantities from {start_date} to {end_date} for store: {store_branch_id}")
        
        # Get all order items for lenses in the specified date range
        sold_quantities = OrderItem.objects.filter(
            order__order_date__gte=start_date,
            order__order_date__lte=end_date,
            lens__isnull=False,
            is_deleted=False,
            order__is_deleted=False,
            order__is_refund=False
        ).values('lens', 'order__branch').annotate(
            total_sold=Sum('quantity')
        )
        
        # Convert to dictionary for faster lookup
        sold_quantities_dict = {}
        for item in sold_quantities:
            if item['total_sold']:
                lens_id = str(item['lens'])
                branch_id = int(item['order__branch'])
                if lens_id not in sold_quantities_dict:
                    sold_quantities_dict[lens_id] = {}
                sold_quantities_dict[lens_id][branch_id] = item['total_sold']
        
        # Get removed quantities for each lens in the date range
        removed_quantities = LensStockHistory.objects.filter(
            action='remove',
            timestamp__range=(start_date, end_date)
        ).values(
            'lens',
            'branch'
        ).annotate(
            total_removed=Sum('quantity_changed')
        )
        
        # Convert to a nested dictionary: {lens_id: {branch_id: removed_count}}
        removed_quantities_dict = {}
        for item in removed_quantities:
            lens_id = str(item['lens'])
            branch_id = item['branch']
            if lens_id not in removed_quantities_dict:
                removed_quantities_dict[lens_id] = {}
            removed_quantities_dict[lens_id][branch_id] = abs(item['total_removed'])  # Take absolute value
        
        # Get all branches except the store branch
        from ..models import Branch
        all_branches = Branch.objects.exclude(id=store_branch_id)
        
        # Get stock quantities for each branch for each lens
        branch_stocks = {}
        branch_transfers = {}
        
        for branch in all_branches:
            # Current stock in branch
            branch_stock = stock_history.filter(
                branch_id=branch.id
            ).values('lens').annotate(
                qty=Sum('quantity_changed')
            )
            
            # Count of lenses received from store branch
            received_from_store = LensStockHistory.objects.filter(
                branch_id=store_branch_id,
                transfer_to=branch,
                action='transfer',
                timestamp__lte=end_date
            ).values('lens').annotate(
                received_count=Sum('quantity_changed')
            )
            
            # Store the received counts
            for item in received_from_store:
                lens_id = item['lens']
                if lens_id not in branch_transfers:
                    branch_transfers[lens_id] = []
                branch_transfers[lens_id].append({
                    'branch_id': branch.id,
                    'branch_name': branch.branch_name,
                    'received_from_store': item['received_count'] or 0
                })
            
            # Store the current stock
            for item in branch_stock:
                lens_id = item['lens']
                if lens_id not in branch_stocks:
                    branch_stocks[lens_id] = []
                branch_stocks[lens_id].append({
                    'branch_id': branch.id,
                    'branch_name': branch.branch_name,
                    'qty': max(0, item['qty'])  # Ensure non-negative
                })
        
        # Prepare the result
        result = []
        for stock in store_stocks:
            lens_id = stock['lens']
            lens = lens_details_dict.get(lens_id)
            if not lens:
                continue
                
            qty = max(0, stock['qty'])  # Ensure non-negative
            other_qty = max(0, other_branches_dict.get(lens_id, 0))
            
            # Get current stock from LensStock for all branches for this lens
            lens_branches = []
            
            # Get all branches that have this lens in stock
            current_stocks = LensStock.objects.filter(
                lens_id=lens_id
            ).select_related('branch')
            
            # Get all branches that received this lens from store (even if they have no current stock)
            all_relevant_branches = set()
            
            # Add branches that have current stock
            for stock in current_stocks:
                all_relevant_branches.add((stock.branch.id, stock.branch.branch_name))
            
            # Add branches that received lenses from store (even if they have no current stock)
            if lens_id in branch_transfers:
                for transfer in branch_transfers[lens_id]:
                    all_relevant_branches.add((transfer['branch_id'], transfer['branch_name']))
            
            # Create the branches array with complete information
            for branch_id, branch_name in all_relevant_branches:
                # Get current stock for this branch
                current_qty = 0
                current_stock = LensStock.objects.filter(
                    lens_id=lens_id,
                    branch_id=branch_id
                ).first()
                
                if current_stock:
                    current_qty = current_stock.qty
                
                # Initialize branch data with current stock, sold and removed quantities
                branch_data = {
                    'branch_id': branch_id,
                    'branch_name': branch_name,
                    'stock_count': max(0, current_qty),  # Current stock count in the branch
                    'stock_received': 0,  # Total received from store
                    'stock_removed': 0,  # Total removed from store
                    'sold_qty': sold_quantities_dict.get(str(lens_id), {}).get(int(branch_id), 0),  # Sold in date range
                }
                
                # Set removed quantity if exists
                if str(lens_id) in removed_quantities_dict and branch_id in removed_quantities_dict[str(lens_id)]:
                    branch_data['stock_removed'] = removed_quantities_dict[str(lens_id)][branch_id]
                
                # Update with received from store count if exists
                if lens_id in branch_transfers:
                    for transfer in branch_transfers[lens_id]:
                        if transfer['branch_id'] == branch_id:
                            received_qty = transfer['received_from_store']
                            branch_data['stock_received'] = received_qty
                            break
                
                lens_branches.append(branch_data)
            
            # Get current stock levels across all branches
            all_branch_stock = LensStock.objects.filter(
                lens_id=lens_id
            ).aggregate(
                total=Sum('qty')
            )['total'] or 0
            
            # Get store branch quantity
            store_qty = current_branch_dict.get(lens_id, 0)
            other_qty = all_branch_stock - store_qty
            
            # Calculate starting inventory (stock at beginning of period)
            starting_stock = LensStockHistory.objects.filter(
                lens_id=lens_id,
                branch_id=store_branch_id,
                timestamp__lt=start_date
            ).aggregate(
                total=Sum('quantity_changed')
            )['total'] or 0
            
            # Calculate additions (positive quantity changes in the period)
            additions = LensStockHistory.objects.filter(
                lens_id=lens_id,
                branch_id=store_branch_id,
                timestamp__range=(start_date, end_date),
                quantity_changed__gt=0
            ).aggregate(
                total=Sum('quantity_changed')
            )['total'] or 0
            
            # Get sales count for the period
            sold_count = sum(sold_quantities_dict.get(str(lens_id), {}).values()) if str(lens_id) in sold_quantities_dict else 0
            
            # Get lens type and coating names
            lens_type = lens.type.name if lens.type else ""
            coating = lens.coating.name if lens.coating else ""
            
            # Get powers for this lens
            powers = LensPower.objects.filter(lens=lens).values('power__name', 'value', 'side')
            
            result.append({
                'lens_id': lens_id,
                'lens_type': lens_type,
                'coating': coating,
                'brand': lens.brand.name if lens.brand else "",
                'starting_stock': starting_stock,
                'additions': additions,
                'sold_count': sold_count,
                'ending_stock': store_qty,
                'other_branches_qty': other_qty,
                'total_available': all_branch_stock,
                'powers': list(powers),
                'as_of_date': end_date.date().isoformat(),
                'branches': lens_branches
            })
            
        return result
        
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        return Response(queryset)