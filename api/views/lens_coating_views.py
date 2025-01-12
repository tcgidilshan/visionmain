from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.permissions import IsAuthenticated
from ..models import Coating
from ..serializers import CoatingSerializer

class LensCoatingListCreateView(ListCreateAPIView):
    """
    Handles listing and creating LensCoating objects.
    """
    queryset = Coating.objects.all()  # Order by creation date
    serializer_class = CoatingSerializer
    permission_classes = [IsAuthenticated]  # Add your custom permissions if needed


class LensCoatingRetrieveUpdateDeleteView(RetrieveUpdateDestroyAPIView):
    """
    Handles retrieving, updating, and deleting a specific LensCoating.
    """
    queryset = Coating.objects.all()
    serializer_class = CoatingSerializer
    permission_classes = [IsAuthenticated]  # Add your custom permissions if needed
