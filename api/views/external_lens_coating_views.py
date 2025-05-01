# views/external_lens_coating_views.py

from rest_framework import generics
from api.models import ExternalLensCoating
from api.serializers import ExternalLensCoatingSerializer

class ExternalLensCoatingListCreateView(generics.ListCreateAPIView):
    """
    List all external lens coatings or create a new one.
    """
    queryset = ExternalLensCoating.objects.all()
    serializer_class = ExternalLensCoatingSerializer


class ExternalLensCoatingRetrieveUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, or delete a specific external lens coating.
    """
    queryset = ExternalLensCoating.objects.all()
    serializer_class = ExternalLensCoatingSerializer
    lookup_field = 'id'
