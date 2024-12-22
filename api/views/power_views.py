from rest_framework import generics, status
from rest_framework.response import Response
from ..models import Power
from ..serializers import PowerSerializer

# List and Create Powers
class PowerListCreateView(generics.ListCreateAPIView):
    queryset = Power.objects.all()
    serializer_class = PowerSerializer

    def list(self, request, *args, **kwargs):
        """
        List all powers.
        """
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        """
        Create a new power.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

# Retrieve, Update, and Delete Powers
class PowerRetrieveUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Power.objects.all()
    serializer_class = PowerSerializer

    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve a single power.
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        """
        Update an existing power.
        """
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        """
        Delete a power.
        """
        instance = self.get_object()
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
