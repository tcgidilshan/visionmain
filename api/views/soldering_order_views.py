from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db import transaction
from decimal import Decimal
from ..services.patient_service import PatientService
from ..models import SolderingOrder, Branch
from ..serializers import SolderingOrderSerializer, SolderingInvoiceSerializer, SolderingPaymentSerializer
from ..services.soldering_order_service import SolderingOrderService
from ..services.soldering_payment_service import SolderingPaymentService
from ..services.soldering_invoice_service import SolderingInvoiceService
from rest_framework.exceptions import ValidationError

class CreateSolderingOrderView(APIView):
    @transaction.atomic
    def post(self, request):
        data = request.data

        # 1. Validate required fields
        required_fields = ['patient', 'branch_id', 'price', 'payments']
        for field in required_fields:
            if field not in data:
                return Response({"error": f"{field} is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # 2. Handle patient creation/updating
            patient = PatientService.create_or_update_patient(data['patient'])

            # 3. Get branch
            branch = get_object_or_404(Branch, id=data['branch_id'])

            # 4. Create order
            order = SolderingOrderService.create_order(
                patient=patient,
                branch=branch,
                price=Decimal(str(data['price'])),
                note=data.get('note', '')
            )

            # 5. Process payments (mandatory)
            payments = SolderingPaymentService.process_solder_payments(order, data['payments'])

            # 6. Generate invoice
            invoice = SolderingInvoiceService.create_invoice(order)

            # 7. Return all results
            return Response({
                "order": SolderingOrderSerializer(order).data,
                "invoice": SolderingInvoiceSerializer(invoice).data,
                "payments": SolderingPaymentSerializer(payments, many=True).data
            }, status=status.HTTP_201_CREATED)

        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": f"Failed to create order: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
