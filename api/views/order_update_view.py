from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from ..models import Order
from ..serializers import OrderSerializer
from ..services.order_service import OrderService
from ..services.patient_service import PatientService

class OrderUpdateView(APIView):
    """
    API View to update an existing order, including stock validation and payments.
    """

    @transaction.atomic
    def put(self, request, pk, *args, **kwargs):
        try:
            order = Order.objects.get(pk=pk)

            # ✅ Step 1: Update Patient Details (if provided)
            patient_data = request.data.get("patient")
            if patient_data:
                PatientService.create_or_update_patient(patient_data)

            # ✅ Step 2: Update Order Using OrderService
            order_data = request.data.get("order", {})
            order_items_data = request.data.get("order_items", [])
            payments_data = request.data.get("order_payments", [])

            updated_order = OrderService.update_order(order, order_data, order_items_data, payments_data)

            # ✅ Step 3: Return Updated Order Response
            response_serializer = OrderSerializer(updated_order)
            return Response(response_serializer.data, status=status.HTTP_200_OK)

        except Order.DoesNotExist:
            return Response({"error": "Order not found."}, status=status.HTTP_404_NOT_FOUND)
        except ValueError as e:
            transaction.set_rollback(True)
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            transaction.set_rollback(True)
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
