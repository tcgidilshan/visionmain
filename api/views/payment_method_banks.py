from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from ..models import PaymentMethodBanks
from ..serializers import PaymentMethodBanksSerializer

class PaymentMethodBanksView(generics.ListCreateAPIView):
    serializer_class = PaymentMethodBanksSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = PaymentMethodBanks.objects.filter(deleted_at__isnull=True)
        branch_id = self.request.query_params.get('branch_id')
        payment_method = self.request.query_params.get('payment_method')
        if branch_id:
            queryset = queryset.filter(branch_id=branch_id)
        if payment_method:
            queryset = queryset.filter(payment_method=payment_method)
        return queryset

    def perform_create(self, serializer):
        serializer.save()

class PaymentMethodBanksDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = PaymentMethodBanks.objects.filter(deleted_at__isnull=True)
    serializer_class = PaymentMethodBanksSerializer
    permission_classes = [IsAuthenticated]

    def perform_update(self, serializer):
        serializer.save()

    def perform_destroy(self, instance):
        instance.deleted_at = timezone.now()
        instance.is_active = False
        instance.save()