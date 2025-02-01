from django.db import transaction
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from ..services.patient_service import PatientService
from ..services.order_service import OrderService
from ..services.stock_validation_service import StockValidationService
from ..services.order_payment_service import OrderPaymentService
from ..services.refraction_details_service import RefractionDetailsService
from ..serializers import OrderSerializer,OrderPaymentSerializer

class ManualOrderCreateView(APIView):
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        try:
            # Step 1: Validate & Create/Update Patient
            patient_data = request.data.get("patient")
            if not patient_data:
                return Response({"error": "Patient details are required."}, status=status.HTTP_400_BAD_REQUEST)

            patient = PatientService.create_or_update_patient(patient_data)

             # Step 2: Create Refraction Details (Optional)
            refraction_details_data = request.data.get("refraction_details")
            refraction_details = None
            if refraction_details_data:
                refraction_details_data["patient"] = patient.id  # Assign the patient
                refraction_details = RefractionDetailsService.create_refraction_details(refraction_details_data)

            # Step 3: Validate Stocks
            order_items_data = request.data.get("order_items", [])
            stock_updates = StockValidationService.validate_stocks(order_items_data)

            # Step 4: Validate Order Data
            order_data = request.data.get("order")
            if not order_data:
                return Response({"error": "Order details are required."}, status=status.HTTP_400_BAD_REQUEST)

            order_data["customer"] = patient.id  # Assign the created patient
            order = OrderService.create_order(order_data, order_items_data)

            # Step 5: Process Payments
            payments_data = request.data.get('order_payments', [])
            if not payments_data:
                return Response({"error": "At least one order payment is required."}, status=status.HTTP_400_BAD_REQUEST)

            total_payment = OrderPaymentService.process_payments(order, payments_data)

            # Step 6: Adjust Stocks (Ensures stocks update only after successful order & payment creation)
            for stock_type, stock, quantity in stock_updates:
                stock.qty -= quantity
                stock.save()

            # Step 7: Return Response
            response_serializer = OrderSerializer(order)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)

        except ValueError as e:
            transaction.set_rollback(True)
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
