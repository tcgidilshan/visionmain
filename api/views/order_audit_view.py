# views.py
from rest_framework.permissions import IsAuthenticated
from rest_framework import generics
from api.models import Invoice, OrderAuditLog, OrderPayment
from django.utils import timezone
from datetime import datetime, timedelta
from rest_framework.generics import ListAPIView
from ..models import Order,OrderItem,OrderPayment,RefractionDetails,OrderAuditLog,Invoice,RefractionDetailsAuditLog,Expense
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from ..serializers import OrderLiteSerializer,OrderSerializer,OrderItemSerializer,OrderPaymentSerializer,ExpenseSerializer
from ..services.pagination_service import PaginationService 
from django.db.models import (
    BooleanField,
    Exists,
    OuterRef,
    Q,
    Value,
    F,
)
from rest_framework.exceptions import ValidationError
from ..services.time_zone_convert_service import TimezoneConverterService

class OrderDeleteRefundListView(ListAPIView):
    pagination_class = PaginationService
    serializer_class = OrderLiteSerializer

    def get_queryset(self):
        status_filter = self.request.query_params.get("status")
        start_date = self.request.query_params.get("start_date")
        end_date = self.request.query_params.get("end_date")
        branch_id = self.request.query_params.get("branch_id")
        start_datetime, end_datetime = TimezoneConverterService.format_date_with_timezone(start_date, end_date)
        queryset = Order.all_objects.select_related('customer', 'branch')
        
        # Decide which records to return
        if status_filter == "deactivated":
            queryset = queryset.filter(is_deleted=True, is_refund=False)
            date_field = "deleted_at"
        elif status_filter == "deactivated_refunded":
            queryset = queryset.filter(is_deleted=True, is_refund=True)
            date_field = "refunded_at"
        elif status_filter == "refunded":
            queryset = queryset.filter(is_refund=True, is_deleted=False)
            date_field = "refunded_at"
        else:  # Active or missing
            queryset = queryset.filter(is_deleted=False, is_refund=False)
            date_field = "order_date"
     
        # Date filtering - Fixed to use proper datetime range filtering
        if start_datetime and end_datetime:
            if start_datetime.date() == end_datetime.date():
                # Same day - use datetime range for timezone-aware fields
                filter_kwargs = {f"{date_field}__range": [start_datetime, end_datetime]}
                queryset = queryset.filter(**filter_kwargs)
            else:
                # Different days - use datetime range
                filter_kwargs = {f"{date_field}__range": [start_datetime, end_datetime]}
                queryset = queryset.filter(**filter_kwargs)
        elif start_datetime:
            filter_kwargs = {f"{date_field}__gte": start_datetime}
            queryset = queryset.filter(**filter_kwargs)
        elif end_datetime:
            filter_kwargs = {f"{date_field}__lte": end_datetime}
            queryset = queryset.filter(**filter_kwargs)
        if branch_id:
            queryset = queryset.filter(branch_id=branch_id)
        return queryset.order_by("-" + date_field)

class OrderAuditHistoryView(APIView):
    """
    Returns all soft-deleted orders, items, and payments.
    """

    def get(self, request):
        # Get soft-deleted records
        order_id = request.query_params.get("order_id")
        order_logs = OrderAuditLog.objects.all()
        order_items = OrderItem.all_objects.filter(is_deleted=True).order_by('-deleted_at')
        # Get ALL payments (active + deleted + edited) for complete audit trail
        order_payments = OrderPayment.all_objects.all().order_by('payment_date')
        # Get order refund expenses
        order_expenses = Expense.objects.none()
        refraction_logs = []
        if order_id:
            order_items = order_items.filter(order_id=order_id)
            order_payments = order_payments.filter(order_id=order_id)
            order_logs = order_logs.filter(order_id=order_id)
            order_expenses = Expense.objects.filter(order_refund_id=order_id, is_refund=True).order_by('-created_at')
            # Fetch refraction details audit logs if applicable
            try:
                order = Order.all_objects.select_related('refraction').get(id=order_id)
                if order.refraction:
                    ref_details = RefractionDetails.objects.filter(refraction_id=order.refraction.id).first()
                    if ref_details:
                        refraction_logs = RefractionDetailsAuditLog.objects.filter(
                            refraction_details=ref_details
                        ).order_by("-created_at")
            except Order.DoesNotExist:
                pass
       
        data = {
            # "orders": OrderSerializer(orders, many=True).data,
            "order_items": OrderItemSerializer(order_items, many=True).data,
            "order_payments": OrderPaymentSerializer(order_payments, many=True).data,
        }

        return Response({
            "order_items": OrderItemSerializer(order_items.order_by('-deleted_at'), many=True).data,
            "order_payments": OrderPaymentSerializer(order_payments.order_by('payment_date'), many=True).data,
            "order_expenses": ExpenseSerializer(order_expenses, many=True).data,
            "order_logs": [
                {
                    "order_id": log.order_id,
                    "field_name": log.field_name,
                    "old_value": log.old_value,
                    "new_value": log.new_value,
                    "user_name": log.user.username if log.user else None,
                    "admin_name": log.admin.username if log.admin else None,
                    "created_at": log.created_at,
                }
                for log in order_logs.order_by('-created_at')
            ],
            "refraction_logs": [
                {
                    "field_name": log.field_name,
                    "old_value": log.old_value,
                    "new_value": log.new_value,
                    "user_name": log.user.username if log.user else None,
                    "admin_name": log.admin.username if log.admin else None,
                    "created_at": log.created_at,
                }
                for log in refraction_logs
            ],
            "invoice_number": Invoice.all_objects.filter(order_id=order_id).values_list('invoice_number', flat=True).first() if order_id else None
        }, status=status.HTTP_200_OK)
class DailyOrderAuditReportView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    pagination_class = PaginationService

    # --------------------------------------------------------------------- #
    # helpers
    # --------------------------------------------------------------------- #
    def _parse_range(self):
        """
        Convert ?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD to timezone-aware
        datetimes covering **[start, end_of_day]**.  Defaults to "today".
        """
        start_str = self.request.query_params.get("start_date")
        end_str   = self.request.query_params.get("end_date")

        start_datetime, end_datetime = TimezoneConverterService.format_date_with_timezone(start_str, end_str)
        print(f"start_datetime: {start_datetime}, end_datetime: {end_datetime}")
        return start_datetime, end_datetime
    # --------------------------------------------------------------------- #
    # main queryset
    # --------------------------------------------------------------------- #
    def get_queryset(self):
        start_datetime, end_datetime = self._parse_range()
        
        # Add validation for None values
        if start_datetime is None or end_datetime is None:
            return Invoice.objects.none()
        
        branch_id = self.request.query_params.get("branch_id")

        # Start with all non-deleted invoices
        qs = Invoice.objects.filter(is_deleted=False)

        # Filter by branch if specified
        if branch_id:
            qs = qs.filter(order__branch_id=branch_id)

        # -- 1️⃣ orders whose *refraction* changed in range ---------------- #
        refraction_sq = RefractionDetailsAuditLog.objects.filter(
            created_at__gte=start_datetime,
            created_at__lte=end_datetime,  # Changed from __lt to __lte
            refraction_details__refraction_id=OuterRef("order__refraction_id")
        )
        qs = qs.annotate(has_refraction_change=Exists(refraction_sq))

        # -- 2️⃣ header-level OrderAuditLog -------------------------------- #
        header_sq = OrderAuditLog.objects.filter(
            order_id=OuterRef("order_id"),
            created_at__gte=start_datetime,
            created_at__lte=end_datetime,  # Changed from __lt to __lte
        )
        qs = qs.annotate(order_details=Exists(header_sq))
        
        # -- 3️⃣ item-level changes (added OR soft-deleted) ---------------- #
        # DEBUG: Check OrderItem model fields
        print(f"=== ORDERITEM DEBUGGING ===")
        print(f"Date range: {start_datetime} to {end_datetime}")
        print(f"OrderItem fields: {[f.name for f in OrderItem._meta.fields]}")
        print(f"OrderItem has created_at: {hasattr(OrderItem, 'created_at')}")
        
        # Check if OrderItem has created_at field in database
        try:
            # Test if created_at field exists in database
            test_item = OrderItem.all_objects.first()
            if test_item:
                created_at_value = getattr(test_item, 'created_at', None)
                print(f"Database has created_at field: {created_at_value is not None}")
                if created_at_value is not None:
                    print(f"Sample created_at value: {created_at_value}")
                else:
                    print("WARNING: created_at field is missing from database!")
        except Exception as e:
            print(f"Error checking created_at field: {e}")
        
        # Check if OrderItem has created_at field
        if hasattr(OrderItem, 'created_at'):
            print(f"OrderItem.created_at field exists in model")
            # Check for items created in date range
            try:
                created_items = OrderItem.all_objects.filter(
                    created_at__gte=start_datetime,
                    created_at__lte=end_datetime
                )
                print(f"Items created in range: {created_items.count()}")
                for item in created_items[:5]:  # Show first 5
                    print(f"  - Item {item.id}: created_at={item.created_at}, order_id={item.order_id}")
            except Exception as e:
                print(f"Error querying created_at: {e}")
                print("This suggests created_at field is missing from database")
        else:
            print("OrderItem model doesn't have created_at field")
        
        # Check for deleted items in date range
        deleted_items = OrderItem.all_objects.filter(
            is_deleted=True,
            deleted_at__gte=start_datetime,
            deleted_at__lte=end_datetime
        )
        print(f"Items deleted in range: {deleted_items.count()}")
        for item in deleted_items[:5]:  # Show first 5
            print(f"  - Deleted Item {item.id}: deleted_at={item.deleted_at}, order_id={item.order_id}")
        
        # Build the item filter
        item_filter = Q(deleted_at__gte=start_datetime, deleted_at__lte=end_datetime)
        if hasattr(OrderItem, "created_at"):
            # Check if created_at field actually exists in database
            try:
                test_query = OrderItem.all_objects.filter(created_at__isnull=False)
                test_query.count()  # This will fail if field doesn't exist
                item_filter |= Q(created_at__gte=start_datetime, created_at__lte=end_datetime)
                print(f"Using both created_at and deleted_at filters")
            except Exception as e:
                print(f"created_at field not available in database: {e}")
                print(f"Only using deleted_at filter")
        else:
            print(f"Only using deleted_at filter (no created_at field)")
        
        # Test the item subquery
        item_sq = OrderItem.all_objects.filter(
            order_id=OuterRef("order_id")
        ).filter(item_filter)
        
        # Debug the subquery by testing with a specific order
        test_order_id = 1  # You can change this to test with a specific order
        test_items = OrderItem.all_objects.filter(
            order_id=test_order_id
        ).filter(item_filter)
        print(f"Test order {test_order_id} has {test_items.count()} items matching filter")
        for item in test_items:
            print(f"  - Test item {item.id}: created_at={getattr(item, 'created_at', 'N/A')}, deleted_at={item.deleted_at}, is_deleted={item.is_deleted}")
        
        qs = qs.annotate(order_item=Exists(item_sq))

        # -- 4️⃣ payment-level changes ------------------------------------- #
        pay_sq = OrderPayment.all_objects.filter(
            order_id=OuterRef("order_id")
        ).filter(
            Q(payment_date__gte=start_datetime, payment_date__lte=end_datetime) |  # Changed from __lt to __lte
            Q(deleted_at__gte=start_datetime, deleted_at__lte=end_datetime)  # Changed from __lt to __lte
        )
        qs = qs.annotate(order_payment=Exists(pay_sq))

        # Filter to only include invoices with at least one type of change
        qs = qs.filter(
            Q(has_refraction_change=True) |
            Q(order_details=True) |
            Q(order_item=True) |
            Q(order_payment=True)
        )
        
        # Debug final results
        final_count = qs.count()
        print(f"Final query returns {final_count} invoices")
        
        # Check which conditions are met for each invoice
        for invoice in qs[:5]:  # Show first 5 results
            print(f"Invoice {invoice.invoice_number} (Order {invoice.order_id}):")
            print(f"  - has_refraction_change: {getattr(invoice, 'has_refraction_change', False)}")
            print(f"  - order_details: {getattr(invoice, 'order_details', False)}")
            print(f"  - order_item: {getattr(invoice, 'order_item', False)}")
            print(f"  - order_payment: {getattr(invoice, 'order_payment', False)}")
        
        return qs.order_by("-invoice_date").distinct()

    # --------------------------------------------------------------------- #
    # response formatter – flatten to plain dicts
    # --------------------------------------------------------------------- #
    def list(self, request, *args, **kwargs):
        print(f"=== LIST METHOD DEBUGGING ===")
        
        base_qs = self.get_queryset().values(
            "invoice_number",
            "order_id",
            "order_details",
            "order_item",
            "order_payment",
            "has_refraction_change",  # Include the actual refraction change value
        ).annotate(
            refraction_details=F("has_refraction_change")  # Use the actual value instead of always True
        )

        # Debug the final data
        final_data = list(base_qs)
        print(f"Final data count: {len(final_data)}")
        
        for item in final_data[:5]:  # Show first 5 items
            print(f"Response item: {item}")
        
        # Check specific OrderItem data for debugging
        print(f"=== CHECKING SPECIFIC ORDERITEM DATA ===")
        start_datetime, end_datetime = self._parse_range()
        
        # Get all OrderItems that should be detected
        all_order_items = OrderItem.all_objects.filter(
            Q(deleted_at__gte=start_datetime, deleted_at__lte=end_datetime) |
            Q(created_at__gte=start_datetime, created_at__lte=end_datetime) if hasattr(OrderItem, 'created_at') else Q()
        )
        
        print(f"Total OrderItems in date range: {all_order_items.count()}")
        
        # Group by order_id to see which orders have item changes
        order_item_changes = {}
        for item in all_order_items:
            order_id = item.order_id
            if order_id not in order_item_changes:
                order_item_changes[order_id] = []
            order_item_changes[order_id].append({
                'id': item.id,
                'created_at': getattr(item, 'created_at', None),
                'deleted_at': item.deleted_at,
                'is_deleted': item.is_deleted
            })
        
        print(f"Orders with item changes: {list(order_item_changes.keys())}")
        for order_id, items in list(order_item_changes.items())[:3]:  # Show first 3 orders
            print(f"Order {order_id} has {len(items)} item changes:")
            for item in items:
                print(f"  - Item {item['id']}: created={item['created_at']}, deleted={item['deleted_at']}, is_deleted={item['is_deleted']}")

        # pagination works on list-of-dicts just fine
        page = self.paginate_queryset(final_data)
        if page is not None:
            return self.get_paginated_response(page)

        return Response(final_data)
