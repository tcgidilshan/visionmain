from django.utils import timezone
from django.core.exceptions import ValidationError
from ..models import SolderingOrder  # adjust path as needed

class SolderingOrderService:
    @staticmethod
    def create_order(*, patient, branch, price, note="", status=None):
        if price <= 0:
            raise ValidationError("Price must be greater than 0.")

        order = SolderingOrder.objects.create(
            patient=patient,
            branch=branch,
            price=price,
            note=note,
            status=status or SolderingOrder.Status.PENDING,
            order_date=timezone.now()
        )

        return order
