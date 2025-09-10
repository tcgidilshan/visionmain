from rest_framework.views import APIView
from rest_framework.response import Response
from ..models import OrderPayment, PaymentMethodBanks  # Adjust import paths as needed
from django.db.models import Sum


class OrderPaymentBankReportViewSet(APIView):
    """
    A viewset for viewing total payments per PaymentMethodBanks (not soft deleted).
    """
    def get(self, request, *args, **kwargs):
        # Aggregate total payments per bank, excluding soft deleted payments
        report = (
            OrderPayment.objects
            .filter(is_deleted=False, payment_method_bank__isnull=False)
            .values('payment_method_bank')
            .annotate(total_amount=Sum('amount'))
        )

        # Optionally, include bank details
        bank_ids = [item['payment_method_bank'] for item in report]
        banks = PaymentMethodBanks.objects.filter(id__in=bank_ids)
        bank_map = {bank.id: bank.name for bank in banks}

        result = [
            {
                "bank_id": item['payment_method_bank'],
                "bank_name": bank_map.get(item['payment_method_bank'], ""),
                "total_amount": float(item['total_amount']) if item['total_amount'] else 0.0
            }
            for item in report
        ]

        return Response(result)