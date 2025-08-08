from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from decimal import Decimal

from ..services.hearing_order_service import HearingOrderService
from ..services.order_payment_service import OrderPaymentService
from ..models import HearingItem, CustomUser

class HearingOrderCreateView(APIView):
    """
    API endpoint for creating hearing aid orders.
    """

    def post(self, request, *args, **kwargs):
        try:
            with transaction.atomic():
                # Extract order data from request
                order_data = request.data.get('order', {})
                order_items = request.data.get('order_items', [])
                payments_data = request.data.get('order_payments', [])

                if not order_items:
                    return Response(
                        {"error": "At least one order item is required"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # For now, we'll use the first item since hearing orders typically have one item
                item_data = order_items[0]
                
                # Get the HearingItem instance
                try:
                    hearing_item = HearingItem.objects.get(id=item_data.get('hearing_item'))
                except HearingItem.DoesNotExist:
                    return Response(
                        {"error": "Hearing item not found"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Get the sales staff user instance
                sales_staff_code = None
                if order_data.get('sales_staff_code'):
                    try:
                        sales_staff_code = CustomUser.objects.get(id=order_data.get('sales_staff_code'))
                    except CustomUser.DoesNotExist:
                        return Response(
                            {"error": "Sales staff not found"},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                
                # Prepare data for HearingOrderService
                service_data = {
                    "patient": request.data.get('patient'),  
                    "hearing_item": hearing_item,  
                    "quantity": item_data.get('quantity', 1),
                    "price_per_unit": item_data.get('price_per_unit', 0),
                    "branch_id": order_data.get('branch_id'),
                    "sales_staff_code": sales_staff_code,
                    "serial_no": item_data.get('serial_no', ''),
                    "battery": item_data.get('battery', ''),
                    "discount": order_data.get('discount', 0),
                    "status": order_data.get('status', 'pending'),
                    "order_remark": order_data.get('order_remark', '')
                }

                # Create the order using the service
                order = HearingOrderService.create(service_data)

                # Process payments if any
                if payments_data:
                    total_paid = OrderPaymentService.process_payments(order, payments_data)
                    
                    # Update order status based on payments
                    if total_paid >= order.total_price:
                        order.status = 'paid'
                    elif total_paid > 0:
                        order.status = 'partially_paid'
                    order.save()

                # Get the invoice data
                invoice = order.invoice
                
                # Prepare response data
                response_data = {
                    "message": "Order created successfully",
                    "order": {
                        "id": order.id,
                     
                        "status": order.status,
                        "sub_total": str(order.sub_total),
                        "discount": str(order.discount) if order.discount else "0.00",
                        "total_price": str(order.total_price),
                    },
                    "invoice": {
                        "id": invoice.id,
                        "invoice_number": invoice.invoice_number,
                        "invoice_type": invoice.get_invoice_type_display(),
                      
                    }
                }

                return Response(response_data, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )