# views.py
from rest_framework.permissions import IsAuthenticated
from rest_framework.generics import ListAPIView
from ..models import Order,OrderItem,OrderPayment,RefractionDetails,OrderAuditLog,Invoice,RefractionDetailsAuditLog
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from ..serializers import OrderLiteSerializer,OrderSerializer,OrderItemSerializer,OrderPaymentSerializer
from ..services.pagination_service import PaginationService  # Use your existing paginator

class OrderDeleteRefundListView(ListAPIView):
    pagination_class = PaginationService
    serializer_class = OrderLiteSerializer

    def get_queryset(self):
        status_filter = self.request.query_params.get("status")
        start_date = self.request.query_params.get("start_date")
        end_date = self.request.query_params.get("end_date")
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

        # Date filtering
        if start_date and end_date:
            if start_date == end_date:
                filter_kwargs = {f"{date_field}__date": start_date}
                queryset = queryset.filter(**filter_kwargs)
            else:
                filter_kwargs = {f"{date_field}__date__range": [start_date, end_date]}
                queryset = queryset.filter(**filter_kwargs)
        elif start_date:
            filter_kwargs = {f"{date_field}__date__gte": start_date}
            queryset = queryset.filter(**filter_kwargs)
        elif end_date:
            filter_kwargs = {f"{date_field}__date__lte": end_date}
            queryset = queryset.filter(**filter_kwargs)

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
        order_payments = OrderPayment.all_objects.filter(is_deleted=True).order_by('-deleted_at')
        refraction_logs = []
        if order_id:
            order_items = order_items.filter(order_id=order_id)
            order_payments = order_payments.filter(order_id=order_id)
            order_logs = order_logs.filter(order_id=order_id)
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
            "order_payments": OrderPaymentSerializer(order_payments.order_by('-deleted_at'), many=True).data,
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