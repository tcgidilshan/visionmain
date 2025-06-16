from django.db.models import Sum
from decimal import Decimal
from ..models import OrderPayment, ChannelPayment, OtherIncome, Expense,SolderingPayment

def get_before_balance(branch_id, date):
    # Sum all order payments, channel payments, other income, soldering, minus all expenses,
    # for ALL days BEFORE the given date.
    order_total = OrderPayment.objects.filter(
        order__branch_id=branch_id,
        payment_date__date__lt=date,
        payment_method="cash"
    ).aggregate(total=Sum('amount'))['total'] or Decimal("0.00")

    channel_total = ChannelPayment.objects.filter(
        appointment__branch_id=branch_id,
        payment_date__date__lt=date,
        payment_method="cash"
    ).aggregate(total=Sum('amount'))['total'] or Decimal("0.00")

    other_income = OtherIncome.objects.filter(
        branch_id=branch_id,
        date__lt=date,
    ).aggregate(total=Sum('amount'))['total'] or Decimal("0.00")

    soldering_income = SolderingPayment.objects.filter(
        order__branch_id=branch_id,
        payment_date__date__lt=date,
        payment_method="cash"
    ).aggregate(total=Sum('amount'))['total'] or Decimal("0.00")

    expenses = Expense.objects.filter(
        branch_id=branch_id,
        created_at__date__lt=date,
        paid_source="cash"
    ).aggregate(total=Sum('amount'))['total'] or Decimal("0.00")

    before_balance = (order_total + channel_total + other_income + soldering_income) - expenses
    return before_balance
