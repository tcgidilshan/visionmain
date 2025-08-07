# services/frame_report_service.py

from datetime import datetime
from django.db.models import Sum
from ..models import OrderItem, Brand, Frame, FrameStock

def generate_frames_report(start_date=None, end_date=None):
    """
    Generates a frames sold report between the given start and end dates.
    """
    # Handle default date range if not provided
    if not start_date or not end_date:
        raise ValueError("Start date and end date are required.")

    try:
        start_date = datetime.strptime(start_date, "%Y-%m-%d")
        end_date = datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError:
        raise ValueError("Dates must be in 'YYYY-MM-DD' format.")

    # Query OrderItems with frames only
    order_items = OrderItem.objects.filter(
        frame__isnull=False,
        order__order_date__range=(start_date, end_date)
    ).select_related(
        'frame__brand', 'frame__code', 'frame__color'
    )

    total_quantity = order_items.aggregate(total=Sum('quantity'))['total'] or 0

    details_list = []
    for item in order_items:
        frame = item.frame
        details_list.append({
            "brand_name": frame.brand.name if frame.brand else None,
            "code": frame.code.name if frame.code else None,
            "color": frame.color.name if frame.color else None,
            "species": frame.species,
            "shape": frame.size,  # Using `size` field as `shape`
            "quantity": item.quantity
        })

    response_data = {
        "summary": {
            "total_frames_sold": total_quantity
        },
        "details": details_list
    }
    
    return response_data

def generate_brand_wise_report(initial_branch_id=None):
    """
    Generates a brand-wise frame report with total stock available and total sold quantities.
    
    Args:
        initial_branch_id (str, optional): Filter frames by initial branch ID if provided
    """
    from django.db.models import Q, F, Sum
    
    # Get all frame brands (BRAND_TYPES = 'frame' or 'both')
    frame_brands = Brand.objects.filter(brand_type='frame')
    
    report_data = []
    total_stock_sum = 0
    total_sold_sum = 0
    
    for brand in frame_brands:
        # Get all frames for this brand
        frames_query = Frame.objects.filter(brand=brand, is_active=True)
        
        # Apply initial_branch filter if provided
        if initial_branch_id:
            frames_query = frames_query.filter(initial_branch_id=initial_branch_id)
        
        # If no frames match the filter, skip this brand
        if not frames_query.exists():
            continue
            
        # Calculate total stock available for these frames across all branches
        # or just the specified branch if initial_branch_id is provided
        stock_query = FrameStock.objects.filter(frame__in=frames_query)
        if initial_branch_id:
            stock_query = stock_query.filter(branch_id=initial_branch_id)
            
        total_stock = stock_query.aggregate(
            total=Sum('qty')
        )['total'] or 0
        
        # Calculate total sold quantity from OrderItems for these frames
        try:
            sold_query = OrderItem.objects.filter(frame__in=frames_query)
            
            # If initial_branch is provided, only count sales from that branch
            if initial_branch_id:
                sold_query = sold_query.filter(order__branch_id=initial_branch_id)
                
            total_sold = sold_query.aggregate(
                total=Sum('quantity')
            )['total'] or 0
        except Exception as e:
            print(f"Error calculating sold quantity: {str(e)}")
            total_sold = 0
        
        # Add to sums
        total_stock_sum += total_stock
        total_sold_sum += total_sold
        
        report_data.append({
            'brand_name': brand.name,
            'total_stock': total_stock,
            'total_sold': total_sold
        })
    
    return {
        'brands': report_data,
        'summary': {
            'total_stock': total_stock_sum,
            'total_sold': total_sold_sum
        }
    }
