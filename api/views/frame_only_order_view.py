from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from ..serializers import FrameOnlyOrderSerializer
from ..serializers import FrameOnlyOrderUpdateSerializer
from ..services.frame_only_order_service import FrameOnlyOrderService
from ..services.order_payment_service import OrderPaymentService
from django.db import transaction
from ..serializers import OrderSerializer  # Optional if you want to return full order
from decimal import Decimal
from datetime import date
from ..models import Order

class FrameOnlyOrderCreateView(APIView):
    """
    Creates a Frame-Only Factory Order.
    """

    def post(self, request, *args, **kwargs):
        serializer = FrameOnlyOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        print(request.data)
        try:
            with transaction.atomic():
                # ✅ FrameOnlyOrderService will now create or reuse the patient
                order = FrameOnlyOrderService.create(serializer.validated_data)

                # Handle payments
                payments_data = request.data.get('payments', [])
                if payments_data:
                    prepared_payments = []
                    for payment in payments_data:
                        payment_copy = payment.copy()
                        payment_copy['order'] = order.id

                        amount = payment_copy.get('amount')
                        if amount is not None:
                            payment_copy['amount'] = Decimal(str(amount))

                        payment_copy['payment_method'] = payment.get('payment_method', 'cash')
                        payment_copy['reference_number'] = payment.get('reference_number')
                        payment_copy['payment_date'] = payment.get('payment_date', str(date.today()))

                        prepared_payments.append(payment_copy)

                    total_paid = OrderPaymentService.process_payments(order, prepared_payments)

                    if total_paid >= order.total_price:
                        order.status = 'paid'
                    elif total_paid > 0:
                        order.status = 'partially_paid'
                    order.save()

        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"detail": f"An unexpected error occurred: {str(e)}"}, 
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        output_serializer = OrderSerializer(order)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)
    
class FrameOnlyOrderUpdateView(APIView):
    def put(self, request, pk):
        try:
            order = Order.objects.get(pk=pk)
            if not order.is_frame_only:
                return Response({"error": "This is not a frame-only order."}, status=400)

            serializer = FrameOnlyOrderUpdateSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            # 1️⃣ Update order (without payments)
            updated_order = FrameOnlyOrderService.update(order, serializer.validated_data)

            # 2️⃣ Handle payments separately
            payments_data = request.data.get("payments", [])
            if payments_data:
                # 🔧 Convert all 'amount' fields to Decimal
                for p in payments_data:
                    if "amount" in p:
                        p["amount"] = Decimal(str(p["amount"]))

                total_paid = OrderPaymentService.update_process_payments(updated_order, payments_data)

                if total_paid >= updated_order.total_price:
                    updated_order.status = "paid"
                elif total_paid > 0:
                    updated_order.status = "partially_paid"
                else:
                    updated_order.status = "pending"
                updated_order.save()

            return Response(OrderSerializer(updated_order).data, status=status.HTTP_200_OK)

        except Order.DoesNotExist:
            return Response({"error": "Order not found."}, status=404)
        except ValueError as e:
            return Response({"error": str(e)}, status=400)
        except Exception as e:
            return Response({"error": str(e)}, status=500)
