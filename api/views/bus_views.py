from rest_framework import generics, status,filters
from rest_framework.response import Response
from ..models import BusSystemSetting
from ..serializers import BusSystemSettingSerializer
from django_filters.rest_framework import DjangoFilterBackend
from ..services.pagination_service import PaginationService

class BusSystemSettingListCreateView(generics.ListCreateAPIView):
    
    """
    Handles listing the bus system title setting and updating it.
    """

    queryset = BusSystemSetting.objects.all()
    serializer_class = BusSystemSettingSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['is_active']  # filter by ?is_active=true/false
    search_fields = ['title']         # search by ?search=some_title
    pagination_class = PaginationService
    def list(self, request, *args, **kwargs):
        """
        Retrieve the current bus system title.
        """
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        """
        Create a new bus system title.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

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
