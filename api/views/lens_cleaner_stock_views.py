from rest_framework import generics, status
from rest_framework.response import Response
from ..models import LensCleanerStock
from ..serializers import LensCleanerStockSerializer

# List and Create Lens Cleaner Stocks
class LensCleanerStockListCreateView(generics.ListCreateAPIView):
    queryset = LensCleanerStock.objects.all()
    serializer_class = LensCleanerStockSerializer

    def list(self, request, *args, **kwargs):
        """
        List all lens cleaner stocks.
        """
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        """
        Create a new lens cleaner stock.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

# Retrieve, Update, and Delete Lens Cleaner Stocks
class LensCleanerStockRetrieveUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    queryset = LensCleanerStock.objects.all()
    serializer_class = LensCleanerStockSerializer

    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve a single lens cleaner stock.
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        """
        Update an existing lens cleaner stock.
        """
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        """
        Delete a lens cleaner stock.
        """
        instance = self.get_object()
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
