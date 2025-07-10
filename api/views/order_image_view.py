from rest_framework import generics
from ..models import OrderImage
from ..serializers import OrderImageSerializer
class OrderImageListCreateView(generics.ListCreateAPIView):
    queryset = OrderImage.objects.all()
    serializer_class = OrderImageSerializer