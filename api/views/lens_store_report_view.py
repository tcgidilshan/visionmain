from rest_framework import generics, filters
from rest_framework.response import Response
from django.db.models import Sum, Q, F, Count
from datetime import datetime
from django.utils import timezone
from rest_framework.views import APIView

from ..models import LensStockHistory, LensStock, OrderItem, Branch, Lens, LenseType, Coating, Brand, LensPower
from ..serializers import LensStockHistorySerializer
from ..services.pagination_service import PaginationService
from ..services.time_zone_convert_service import TimezoneConverterService

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

# Replace the existing LensSaleReportView class with this one
class LensSaleReportView(APIView):
    def get(self, request, *args, **kwargs):
        store_branch_id = request.query_params.get('store_branch_id')
        date_start = request.query_params.get('date_start')
        date_end = request.query_params.get('date_end')
        
        # Use TimezoneConverterService for consistent date handling
        start_datetime, end_datetime = TimezoneConverterService.format_date_with_timezone(date_start, date_end)
        if not start_datetime or not end_datetime:
            return Response({'error': 'Invalid date format'}, status=400)
        
        # Get lenses based on store_branch_id (if provided)
        if store_branch_id:
            # Find all lenses that have stock in the specified store
            lens_ids = LensStock.objects.filter(
                branch_id=store_branch_id,
                qty__gte=0  # Include lenses with zero quantity
            ).values_list('lens_id', flat=True).distinct()
            
            lenses = Lens.objects.filter(id__in=lens_ids).select_related(
                'type', 'coating', 'brand'
            )
        else:
            # Get all lenses if store_branch_id is not provided
            lenses = Lens.objects.all().select_related(
                'type', 'coating', 'brand'
            )
        
        lens_ids = [lens.id for lens in lenses]
        
        # Create lookup dictionaries for quick access
        lens_dict = {lens.id: lens for lens in lenses}
        
        # Get all branches
        all_branches = Branch.objects.all()
        branch_dict = {branch.id: branch for branch in all_branches}
        
        # Get current stock levels for these lenses from LensStock
        current_stocks = LensStock.objects.filter(
            lens_id__in=lens_ids
        ).values('lens_id', 'branch_id', 'qty')
        
        # Group stocks by lens_id and branch_id
        stock_by_lens_branch = {}
        for stock in current_stocks:
            lens_id = stock['lens_id']
            branch_id = stock['branch_id']
            qty = stock['qty']
            
            if lens_id not in stock_by_lens_branch:
                stock_by_lens_branch[lens_id] = {}
                
            stock_by_lens_branch[lens_id][branch_id] = qty
        
        # Get total stock by lens
        total_stock_by_lens = {}
        store_stock_by_lens = {}
        other_stock_by_lens = {}
        
        for lens_id, branch_stocks in stock_by_lens_branch.items():
            total = sum(branch_stocks.values())
            
            # If store_branch_id is provided, separate store stock and other branches
            if store_branch_id:
                store_qty = branch_stocks.get(int(store_branch_id), 0)
                other_qty = total - store_qty
            else:
                # Without a specific store, consider all stock as "store" stock
                store_qty = total
                other_qty = 0
            
            total_stock_by_lens[lens_id] = total
            store_stock_by_lens[lens_id] = store_qty
            other_stock_by_lens[lens_id] = other_qty
        
        # Get sold quantities within date range by branch
        sold_items = OrderItem.objects.filter(
            lens_id__in=lens_ids,
            is_deleted=False,
            order__is_deleted=False,
            order__is_refund=False,
            order__order_date__gte=start_datetime,
            order__order_date__lte=end_datetime
        ).values('lens_id', 'order__branch_id').annotate(sold_count=Sum('quantity'))
        
        # Group sold quantities by lens_id and branch_id
        sold_by_lens_branch = {}
        for item in sold_items:
            lens_id = item['lens_id']
            branch_id = item['order__branch_id']
            count = item['sold_count'] or 0
            
            if lens_id not in sold_by_lens_branch:
                sold_by_lens_branch[lens_id] = {}
                
            sold_by_lens_branch[lens_id][branch_id] = count
        
        # Calculate total sold by lens
        sold_by_lens = {}
        for lens_id, branch_sales in sold_by_lens_branch.items():
            sold_by_lens[lens_id] = sum(branch_sales.values())
        
        # Get received stock (transfers to branch from store)
        if store_branch_id:
            received_stock = LensStockHistory.objects.filter(
                lens_id__in=lens_ids,
                branch_id=store_branch_id,
                action='transfer',
                timestamp__gte=start_datetime,
                timestamp__lte=end_datetime
            ).values('lens_id', 'transfer_to_id').annotate(received_count=Sum('quantity_changed'))
        else:
            # If no store_branch_id, get all transfers
            received_stock = LensStockHistory.objects.filter(
                lens_id__in=lens_ids,
                action='transfer',
                timestamp__gte=start_datetime,
                timestamp__lte=end_datetime
            ).values('lens_id', 'transfer_to_id').annotate(received_count=Sum('quantity_changed'))
            
        # Group received stock by lens_id and branch_id
        received_by_lens_branch = {}
        for item in received_stock:
            lens_id = item['lens_id']
            branch_id = item['transfer_to_id']
            count = item['received_count'] or 0
            
            if lens_id not in received_by_lens_branch:
                received_by_lens_branch[lens_id] = {}
                
            received_by_lens_branch[lens_id][branch_id] = count
        
        # Get removed stock (removals from any branch)
        removed_stock = LensStockHistory.objects.filter(
            lens_id__in=lens_ids,
            action='remove',
            timestamp__gte=start_datetime,
            timestamp__lte=end_datetime
        ).values('lens_id', 'branch_id').annotate(removed_count=Sum('quantity_changed'))
        
        # Group removed stock by lens_id and branch_id
        removed_by_lens_branch = {}
        for item in removed_stock:
            lens_id = item['lens_id']
            branch_id = item['branch_id']
            count = abs(item['removed_count'] or 0)  # Make sure it's positive
            
            if lens_id not in removed_by_lens_branch:
                removed_by_lens_branch[lens_id] = {}
                
            removed_by_lens_branch[lens_id][branch_id] = count
        
        # Calculate starting inventory for each lens at the store branch
        starting_stock_by_lens = {}
        if store_branch_id:
            starting_stocks = LensStockHistory.objects.filter(
                lens_id__in=lens_ids,
                branch_id=store_branch_id,
                timestamp__lt=start_datetime
            ).values('lens_id').annotate(
                starting_qty=Sum('quantity_changed')
            )
            for item in starting_stocks:
                starting_stock_by_lens[item['lens_id']] = item['starting_qty'] or 0
        
        # Calculate additions (positive quantity changes in the period)
        additions_by_lens = {}
        if store_branch_id:
            additions = LensStockHistory.objects.filter(
                lens_id__in=lens_ids,
                branch_id=store_branch_id,
                timestamp__range=(start_datetime, end_datetime),
                quantity_changed__gt=0
            ).values('lens_id').annotate(
                added=Sum('quantity_changed')
            )
            for item in additions:
                additions_by_lens[item['lens_id']] = item['added'] or 0
        
        # Get powers for each lens
        all_powers = LensPower.objects.filter(
            lens_id__in=lens_ids
        ).select_related('power').values(
            'lens_id',
            'power',
            'value',
            'side',
            power_name=F('power__name')
        )
        
        # Group powers by lens_id
        powers_by_lens = {}
        for power in all_powers:
            lens_id = power['lens_id']
            if lens_id not in powers_by_lens:
                powers_by_lens[lens_id] = []
            powers_by_lens[lens_id].append(power)
        
        # Build the result
        result = []
        for lens_id in lens_ids:
            lens = lens_dict.get(lens_id)
            if not lens:
                continue
                
            # Get branch data for this lens - include ALL branches
            branches_data = []
            
            for branch in all_branches:
                branch_id = branch.id
                
                # Always include each branch, regardless of activity
                branch_data = {
                    'branch_id': branch_id,
                    'branch_name': branch.branch_name,
                    'stock_count': stock_by_lens_branch.get(lens_id, {}).get(branch_id, 0),
                    'stock_received': received_by_lens_branch.get(lens_id, {}).get(branch_id, 0),
                    'stock_removed': removed_by_lens_branch.get(lens_id, {}).get(branch_id, 0),
                    'sold_qty': sold_by_lens_branch.get(lens_id, {}).get(branch_id, 0) or 0
                }
                
                branches_data.append(branch_data)
            
            # Calculate stock values
            store_branch_qty = store_stock_by_lens.get(lens_id, 0)
            other_branches_qty = other_stock_by_lens.get(lens_id, 0)
            total_qty = total_stock_by_lens.get(lens_id, 0)
            
            result.append({
                'lens_id': lens_id,
                'lens_type': lens.type.name if lens.type else "",
                'coating': lens.coating.name if lens.coating else "",
                'brand': lens.brand.name if lens.brand else "",
                'starting_stock': starting_stock_by_lens.get(lens_id, 0),
                'additions': additions_by_lens.get(lens_id, 0),
                'store_branch_qty': store_branch_qty,
                'other_branches_qty': other_branches_qty,
                'total_qty': total_qty,
                'total_available': total_qty,
                'sold_count': sold_by_lens.get(lens_id, 0),
                'ending_stock': store_branch_qty,  # Same as store_branch_qty
                'powers': powers_by_lens.get(lens_id, []),  # Include lens powers
                'as_of_date': end_datetime.date().isoformat(),
                'branches': branches_data
            })
        
        return Response(result, status=200)