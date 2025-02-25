from rest_framework import generics, status
from rest_framework.response import Response
from ..models import LensCleaner
from ..serializers import LensCleanerSerializer
from rest_framework.permissions import IsAuthenticated

# List and Create Lens Cleaners
class LensCleanerListCreateView(generics.ListCreateAPIView):
    queryset = LensCleaner.objects.filter(is_active=True)  # ✅ Prefetch related stocks
    serializer_class = LensCleanerSerializer
    permission_classes = [IsAuthenticated] 

    def list(self, request, *args, **kwargs):
        """
        List all lens cleaners.
        """
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        """
        Create a new lens cleaner.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

# Retrieve, Update, and Delete Lens Cleaners
class LensCleanerRetrieveUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    queryset = LensCleaner.objects.prefetch_related('stocks').all()  # ✅ Prefetch related stocks
    serializer_class = LensCleanerSerializer
    permission_classes = [IsAuthenticated] 

    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve a single lens cleaner.
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        """
        Update an existing lens cleaner.
        """
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        is_active = request.data.get("is_active", instance.is_active) 
        instance.is_active = is_active
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        """
        Override delete to implement soft deletion.
        """
        instance = self.get_object()
        instance.is_active = False  # ✅ Soft delete instead of removing
        instance.save()
        return Response({"message": "Lens Cleaner marked as inactive."}, status=status.HTTP_200_OK)

