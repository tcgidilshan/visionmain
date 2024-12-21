from rest_framework import generics, status
from rest_framework.response import Response
from ..models import FrameStock
from ..serializers import FrameStockSerializer

# List and Create FrameStock Records
class FrameStockListCreateView(generics.ListCreateAPIView):
    queryset = FrameStock.objects.all()
    serializer_class = FrameStockSerializer

    def list(self, request, *args, **kwargs):
        """
        List all FrameStock records.
        """
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        """
        Create a new FrameStock record.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

# Retrieve, Update, and Delete FrameStock Records
class FrameStockRetrieveUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    queryset = FrameStock.objects.all()
    serializer_class = FrameStockSerializer

    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve a single FrameStock record.
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        """
        Update an existing FrameStock record.
        """
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        """
        Delete a FrameStock record.
        """
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)
