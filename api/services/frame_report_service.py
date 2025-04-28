# services/frame_report_service.py

from datetime import datetime
from django.db.models import Sum
from ..models import OrderItem

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
