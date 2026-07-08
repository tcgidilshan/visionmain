# services/frame_report_service.py

from datetime import datetime
from django.db.models import Sum
from ..models import OrderItem, Brand, Frame, FrameStock
from ..constants import FRAME_STORE_BRANCH_ID

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

def generate_brand_wise_report(initial_branch_id=None, brand_name=None, branch_id=None, start_date=None, end_date=None):
    """
    Brand-wise frame report.
    Returns per brand:
      - branch_stock    : qty in the current branch (branch_id)
      - total_sold      : units sold, optionally filtered by date range
      - total_available : qty summed across ALL branches
      - store_stock     : qty in the frame store branch (branch_id=4)
    """
    from django.db.models import Sum
    from ..services.time_zone_convert_service import TimezoneConverterService

    start_datetime, end_datetime = TimezoneConverterService.format_date_with_timezone(start_date, end_date)

    frame_brands = Brand.objects.filter(brand_type='frame')
    if brand_name:
        frame_brands = frame_brands.filter(name__icontains=brand_name)

    report_data = []
    summary_branch_stock = 0
    summary_total_sold = 0
    summary_total_available = 0
    summary_store_stock = 0

    for brand in frame_brands:
        frames_query = Frame.objects.filter(brand=brand, is_active=True)
        if initial_branch_id:
            frames_query = frames_query.filter(initial_branch_id=initial_branch_id)
        if not frames_query.exists():
            continue

        branch_stock = 0
        if branch_id:
            branch_stock = FrameStock.objects.filter(
                frame__in=frames_query,
                branch_id=branch_id
            ).aggregate(total=Sum('qty'))['total'] or 0

        total_available = FrameStock.objects.filter(
            frame__in=frames_query
        ).aggregate(total=Sum('qty'))['total'] or 0

        store_stock = FrameStock.objects.filter(
            frame__in=frames_query,
            branch_id=FRAME_STORE_BRANCH_ID
        ).aggregate(total=Sum('qty'))['total'] or 0

        sold_qs = OrderItem.objects.filter(frame__in=frames_query)
        if start_datetime and end_datetime:
            sold_qs = sold_qs.filter(
                order__order_date__gte=start_datetime,
                order__order_date__lte=end_datetime
            )
        total_sold = sold_qs.aggregate(total=Sum('quantity'))['total'] or 0

        summary_branch_stock += branch_stock
        summary_total_sold += total_sold
        summary_total_available += total_available
        summary_store_stock += store_stock

        report_data.append({
            'brand_name': brand.name,
            'branch_stock': branch_stock,
            'total_sold': total_sold,
            'total_available': total_available,
            'store_stock': store_stock,
        })

    return {
        'brands': report_data,
        'summary': {
            'total_branch_stock': summary_branch_stock,
            'total_sold': summary_total_sold,
            'total_available': summary_total_available,
            'total_store_stock': summary_store_stock,
        }
    }

def generate_branch_wise_frame_brand_report(branch_id, brand_name=None, start_date=None, end_date=None,
                                             sort_by=None, sort_order='asc'):
    """
    Per-brand report for the given branch:
      - branch_stock      : qty in the requested branch
      - total_sold        : units sold (orders from this branch, optionally filtered by date)
      - total_available   : qty summed across ALL branches
      - store_stock       : qty in the frame store branch (branch_id=4)
      - other_branches_stock : qty available in all branches except the requested branch_id
                                and the frame store branch (branch_id=4)

    sort_by: one of 'brand_name', 'branch_stock', 'store_stock', 'total_sold',
             'total_available', 'all_stock', 'other_branches_stock'. Defaults to no
             sorting (insertion order).
    sort_order: 'asc' or 'desc'.

    If neither start_date nor end_date is provided, total_sold is the
    all-time count of OrderItems for the given branch_id (no date filter).
    """
    from django.db.models import Sum
    from ..services.time_zone_convert_service import TimezoneConverterService

    start_datetime, end_datetime = (None, None)
    if start_date or end_date:
        start_datetime, end_datetime = TimezoneConverterService.format_date_with_timezone(start_date, end_date)

    frame_brands = Brand.objects.filter(brand_type='frame')
    if brand_name:
        frame_brands = frame_brands.filter(name__icontains=brand_name)

    report_data = []
    summary_branch_stock = 0
    summary_total_sold = 0
    summary_total_available = 0
    summary_store_stock = 0
    summary_other_branches_stock = 0

    for brand in frame_brands:
        frames = Frame.objects.filter(brand=brand, is_active=True)
        if not frames.exists():
            continue

        branch_stock = FrameStock.objects.filter(
            frame__in=frames,
            branch_id=branch_id
        ).aggregate(total=Sum('qty'))['total'] or 0

        total_available = FrameStock.objects.filter(
            frame__in=frames
        ).aggregate(total=Sum('qty'))['total'] or 0

        store_stock = FrameStock.objects.filter(
            frame__in=frames,
            branch_id=FRAME_STORE_BRANCH_ID
        ).aggregate(total=Sum('qty'))['total'] or 0

        other_branches_stock = FrameStock.objects.filter(
            frame__in=frames
        ).exclude(
            branch_id__in={branch_id, FRAME_STORE_BRANCH_ID}
        ).aggregate(total=Sum('qty'))['total'] or 0

        sold_qs = OrderItem.objects.filter(
            frame__in=frames,
            order__branch_id=branch_id
        )
        if start_datetime and end_datetime:
            sold_qs = sold_qs.filter(
                order__order_date__gte=start_datetime,
                order__order_date__lte=end_datetime
            )
        total_sold = sold_qs.aggregate(total=Sum('quantity'))['total'] or 0

        summary_branch_stock += branch_stock
        summary_total_sold += total_sold
        summary_total_available += total_available
        summary_store_stock += store_stock
        summary_other_branches_stock += other_branches_stock

        report_data.append({
            'brand_name': brand.name,
            'branch_stock': branch_stock,
            'total_sold': total_sold,
            'total_available': total_available,
            'store_stock': store_stock,
            'other_branches_stock': other_branches_stock,
        })

    if sort_by:
        sort_key_map = {
            'brand_name': lambda item: (item['brand_name'] or '').lower(),
            'branch_stock': lambda item: item['branch_stock'],
            'store_stock': lambda item: item['store_stock'],
            'total_sold': lambda item: item['total_sold'],
            'total_available': lambda item: item['total_available'],
            'all_stock': lambda item: item['store_stock'] + item['total_available'],
            'other_branches_stock': lambda item: item['other_branches_stock'],
        }
        key_func = sort_key_map.get(sort_by)
        if key_func:
            report_data.sort(key=key_func, reverse=(sort_order == 'desc'))

    return {
        'brands': report_data,
        'summary': {
            'total_branch_stock': summary_branch_stock,
            'total_sold': summary_total_sold,
            'total_available': summary_total_available,
            'total_store_stock': summary_store_stock,
            'total_other_branches_stock': summary_other_branches_stock,
        }
    }
