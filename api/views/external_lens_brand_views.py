# views/external_lens_brand_views.py

from rest_framework import generics
from api.models import ExternalLensBrand
from api.serializers import ExternalLensBrandSerializer

class ExternalLensBrandListCreateView(generics.ListCreateAPIView):
    """
    List all external lens brands or create a new one.
    """
    queryset = ExternalLensBrand.objects.all()
    serializer_class = ExternalLensBrandSerializer


class ExternalLensBrandRetrieveUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, or delete a specific external lens brand.
    """
    queryset = ExternalLensBrand.objects.all()
    serializer_class = ExternalLensBrandSerializer
    lookup_field = 'id'
