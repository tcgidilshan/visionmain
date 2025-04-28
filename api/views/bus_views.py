from rest_framework import generics, status
from rest_framework.response import Response
from ..models import BusSystemSetting
from ..serializers import BusSystemSettingSerializer


class BusSystemSettingListCreateView(generics.ListCreateAPIView):
    """
    Handles listing the bus system title setting and updating it.
    """
    queryset = BusSystemSetting.objects.all()
    serializer_class = BusSystemSettingSerializer

    def list(self, request, *args, **kwargs):
        """
        Retrieve the current bus system title.
        """
        instance = self.get_queryset().first()
        
        if not instance:
            return Response({"detail": "No title setting found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        """
        Create or update the bus system title setting.
        If a setting already exists, it updates the existing one instead of creating a new entry.
        """
        instance = self.get_queryset().first()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer) if not instance else self.perform_update(serializer)
        return Response(serializer.data, status=status.HTTP_200_OK if instance else status.HTTP_201_CREATED)


class BusSystemSettingRetrieveUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    """
    Handles retrieving, updating, and deleting the bus system title setting.
    """
    queryset = BusSystemSetting.objects.all()
    serializer_class = BusSystemSettingSerializer

    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve the current bus system title setting.
        """
        instance = self.get_queryset().first()
        
        if not instance:
            return Response({"detail": "No title setting found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        """
        Update the bus system title setting.
        """
        instance = self.get_queryset().first()
        
        if not instance:
            return Response({"detail": "No title setting found to update."}, status=status.HTTP_404_NOT_FOUND)

        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        """
        Reset the bus system title setting (delete it).
        """
        instance = self.get_queryset().first()
        
        if not instance:
            return Response({"detail": "No title setting found to delete."}, status=status.HTTP_404_NOT_FOUND)

        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)
