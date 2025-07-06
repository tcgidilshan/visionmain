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
        
        # Get sold quantities for each lens per branch in the specified date range
        print(f"\n=== DEBUG: Fetching sold quantities from {start_date} to {end_date} for store: {store_branch_id}")
        
        # Get all order items for lenses in the specified date range
        sold_items = OrderItem.objects.filter(
            order__order_date__range=(start_date, end_date),
            lens__isnull=False
        ).values('lens').annotate(
            sold_qty=Sum('quantity')
        )
        
        # Create a dictionary of lens_id to sold quantity
        sold_dict = {item['lens']: item['sold_qty'] for item in sold_items}
        
        # Prepare the final data
        result = []
        for lens_id, lens in lens_details_dict.items():
            current_qty = current_branch_dict.get(lens_id, 0)
            sold_qty = sold_dict.get(lens_id, 0)
            
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
                'current_quantity': current_qty,
                'sold_quantity': sold_qty,
                'powers': list(powers)
            })
        
        return result
        
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        
        # For ListAPIView, we'll return the data directly since we've already formatted it
        return Response(queryset)