from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from ..models import Order,ExternalLens
from ..serializers import OrderSerializer,ExternalLensSerializer
from ..services.order_service import OrderService
from ..services.patient_service import PatientService
from ..services.external_lens_service import ExternalLensService
from rest_framework.exceptions import ValidationError

class OrderUpdateView(APIView):
    """
    API View to update an existing order, including external lenses, stock validation, and payments.
    """

    @transaction.atomic
    def put(self, request, pk, *args, **kwargs):
        try:
            order = Order.objects.get(pk=pk)

            # ✅ Step 1: Update Patient Details (if provided)
            patient_data = request.data.get("patient")
            if patient_data:
                PatientService.create_or_update_patient(patient_data)

            # ✅ Step 2: Extract Order Data (check if on_hold status is changing)
            order_data = request.data.get("order", {})
            order_items_data = request.data.get("order_items", [])
            payments_data = request.data.get("order_payments", [])

            # ✅ Check if we're changing on_hold status
            current_on_hold = order.on_hold
            new_on_hold = order_data.get("on_hold", current_on_hold)
            
            # Log the on-hold transition if it's happening (can be helpful for debugging)
            if current_on_hold != new_on_hold:
                print(f"Order {order.id} on_hold status changing: {current_on_hold} → {new_on_hold}")

            # ✅ Step 3: Update Order 
            # The updated update_order method now handles different stock behavior based on on_hold status
            updated_order = OrderService.update_order(order, order_data, order_items_data, payments_data)

            # ✅ Step 5: Return Updated Order Response
            response_serializer = OrderSerializer(updated_order)
            return Response(response_serializer.data, status=status.HTTP_200_OK)

        except Order.DoesNotExist:
            return Response({"error": "Order not found."}, status=status.HTTP_404_NOT_FOUND)
        except ExternalLens.DoesNotExist:
            return Response({"error": "External lens not found."}, status=status.HTTP_400_BAD_REQUEST)
        except ValidationError as e:
            transaction.set_rollback(True)
            return Response({"error": e.detail}, status=status.HTTP_400_BAD_REQUEST)
        except ValueError as e:
            transaction.set_rollback(True)
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            transaction.set_rollback(True)
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)