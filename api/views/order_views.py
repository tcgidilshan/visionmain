from django.db import transaction
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from ..models import Order, OrderItem, OrderPayment, LensStock, LensCleanerStock, FrameStock,RefractionDetails,Refraction
from ..serializers import OrderSerializer, OrderItemSerializer, OrderPaymentSerializer
from ..services.order_payment_service import OrderPaymentService
from ..services.stock_validation_service import StockValidationService
from ..services.order_service import OrderService
from ..services.patient_service import PatientService
from ..services.Invoice_service import InvoiceService
from ..services.refraction_details_service import RefractionDetailsService

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

                # ✅ If refraction_id is provided, update patient_id in Refraction table
                refraction_id = patient_data.get("refraction_id")
                if refraction_id:
                    try:
                        refraction = Refraction.objects.get(id=refraction_id)
                        refraction.patient = patient  # ✅ Assign the patient
                        refraction.save()
                    except Refraction.DoesNotExist:
                        return Response({"error": "Refraction record not found."}, status=status.HTTP_400_BAD_REQUEST)

                # ✅ Step 4: Create Refraction Details (Only if provided)
                refraction_details_data = request.data.get("refraction_details")
                refraction_details = None
                if refraction_details_data: 
                    refraction_details_data["patient"] = patient.id  # ✅ Assign the patient ID
                    refraction_details = RefractionDetailsService.create_refraction_details(refraction_details_data)

                else:
                    # ✅ No new refraction details provided -> Find & update existing one
                    refraction_id = patient.refraction_id  # Get `refraction_id` from Patient
                    if refraction_id:
                        try:
                            # ✅ Find the existing refraction details for the patient's refraction_id
                            refraction_details = RefractionDetails.objects.get(refraction_id=refraction_id)
                            # ✅ Update the patient_id column in that row
                            refraction_details.patient_id = patient.id
                            refraction_details.save()
                        except RefractionDetails.DoesNotExist:
                            pass  # ✅ If no existing refraction details, do nothing
                
                # Step 5: Validate Stocks Using Service
                order_items_data = request.data.get('order_items', [])
                stock_items = [item for item in order_items_data if not item.get('is_non_stock', False)]  # 🔥 Filter only stock-based items (exclude is_non_stock=True)
                stock_updates = StockValidationService.validate_stocks(stock_items) if stock_items else [] # 🔍 Validate stock only for stock items

                # Step 6: Create Order and Order Items Using Service
                order_data = request.data.get('order')

                if not order_data:
                    return Response({"error": "The 'order' field is required."}, status=status.HTTP_400_BAD_REQUEST)
                
                order_data["customer"] = patient.id  # ✅ Automatically assign the newly created patient
                order = OrderService.create_order(order_data, order_items_data)

                # ✅ Step 7: Generate Invoice Based on New Scenario
                InvoiceService.create_invoice(order)

                # Step 8: Create Order Payments
                payments_data = request.data.get('order_payments', [])
                if not payments_data:
                    raise ValueError("At least one order payment is required.")

                total_payment = OrderPaymentService.process_payments(order, payments_data)

                # Ensure total payment does not exceed the order total price
                if total_payment > order.total_price:
                    raise ValueError("Total payments exceed the order total price.")

               # Step 9: Adjust Stocks (Only for Stock Items)
                StockValidationService.adjust_stocks(stock_updates)

                # Return successful response
                response_serializer = OrderSerializer(order)
                return Response(response_serializer.data, status=201)

        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
