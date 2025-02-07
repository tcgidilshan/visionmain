from django.db import transaction
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from ..models import Order, OrderItem, OrderPayment, LensStock, LensCleanerStock, FrameStock
from ..serializers import OrderSerializer, OrderItemSerializer, OrderPaymentSerializer
from ..services.order_payment_service import OrderPaymentService
from ..services.stock_validation_service import StockValidationService
from ..services.order_service import OrderService
from ..services.patient_service import PatientService

class OrderCreateView(APIView):

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        """
        Create an order with stock validation, order creation, and stock adjustment.
        """
        try:
            # Step 1: Start transaction
            with transaction.atomic():

                # Step 2: Validate & Create/Update Patient Using Service
                patient_data = request.data.get("patient")
                if not patient_data:
                    return Response({"error": "Patient details are required."}, status=status.HTTP_400_BAD_REQUEST)
                
                patient = PatientService.create_or_update_patient(patient_data)  # ✅ Create or update patient
                
                # Step 3: Validate Stocks Using Service
                order_items_data = request.data.get('order_items', [])
                stock_updates = StockValidationService.validate_stocks(order_items_data)

                # Step 4: Create Order and Order Items Using Service
                order_data = request.data.get('order')
                order_data["customer"] = patient.id  # ✅ Automatically assign the newly created patient
                order = OrderService.create_order(order_data, order_items_data)

                # Step 5: Create Order Payments
                payments_data = request.data.get('order_payments', [])
                if not payments_data:
                    raise ValueError("At least one order payment is required.")

                total_payment = OrderPaymentService.process_payments(order, payments_data)

                # Ensure total payment does not exceed the order total price
                if total_payment > order.total_price:
                    raise ValueError("Total payments exceed the order total price.")

                # Step 6: Adjust Stocks
                for stock_type, stock, quantity in stock_updates:
                    stock.qty -= quantity
                    stock.save()

                # Return successful response
                response_serializer = OrderSerializer(order)
                return Response(response_serializer.data, status=201)

        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
