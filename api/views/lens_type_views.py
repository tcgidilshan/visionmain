from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.permissions import IsAuthenticated
from ..models import LenseType
from ..serializers import LenseTypeSerializer

class LensTypeListCreateView(ListCreateAPIView):
    """
    Handles listing and creating LensType objects.
    """
    queryset = LenseType.objects.all() 
    serializer_class = LenseTypeSerializer
    permission_classes = [IsAuthenticated]  # Add your custom permissions if needed


class LensTypeRetrieveUpdateDeleteView(RetrieveUpdateDestroyAPIView):
    """
    Handles retrieving, updating, and deleting a specific LensType.
    """
    queryset = LenseType.objects.all()
    serializer_class = LenseTypeSerializer
    permission_classes = [IsAuthenticated]  # Add your custom permissions if needed
