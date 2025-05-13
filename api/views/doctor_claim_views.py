from ..serializers import DoctorClaimInvoiceSerializer,DoctorClaimChannelSerializer
from rest_framework import generics, status,filters
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from ..services.pagination_service import PaginationService
from ..models import DoctorClaimInvoice,DoctorClaimChannel

class DoctorClaimInvoiceListCreateView(generics.ListCreateAPIView):
    """
    Handles listing and creating doctor claim invoices.
    """
    queryset = DoctorClaimInvoice.objects.all()
    serializer_class = DoctorClaimInvoiceSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['invoice_number','branch_id']  
    pagination_class = PaginationService

    def get_queryset(self):
        """
        Override to add date range filtering.
        """
        queryset = super().get_queryset()
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)
            
        return queryset    

    def list(self, request, *args, **kwargs):
        """
        Retrieve the current doctor claim invoice list.
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
        Create a new doctor claim invoice.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class DoctorClaimInvoiceRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    """
    Handles retrieving, updating, and deleting a specific doctor claim invoice.
    """
    queryset = DoctorClaimInvoice.objects.all()
    serializer_class = DoctorClaimInvoiceSerializer

    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve a specific doctor claim invoice.
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    def update(self, request, *args, **kwargs):
        """
        Update a specific doctor claim invoice.
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)
    
    def destroy(self, request, *args, **kwargs):
        """
        Delete a specific doctor claim invoice.
        """
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

class DoctorClaimChannelListCreateView(generics.ListCreateAPIView):
    """
    Handles listing and creating doctor claim channels.
    """
    queryset = DoctorClaimChannel.objects.all()
    serializer_class = DoctorClaimChannelSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['invoice_number','branch_id']  # filter by ?is_active=true/false
    pagination_class = PaginationService
    def get_queryset(self):
        """
        Override to add date range filtering.
        """
        queryset = super().get_queryset()
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)
            
        return queryset    
    
    def list(self, request, *args, **kwargs):
        """
        Retrieve the current doctor claim channel list.
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
        Create a new doctor claim channel.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class DoctorClaimChannelRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    """
    Handles retrieving, updating, and deleting a specific doctor claim channel.
    """
    queryset = DoctorClaimChannel.objects.all()
    serializer_class = DoctorClaimChannelSerializer
    
def retrieve(self, request, *args, **kwargs):
    """
    Retrieve a specific doctor claim channel.
    """
    instance = self.get_object()
    serializer = self.get_serializer(instance)
    return Response(serializer.data)
    
def update(self, request, *args, **kwargs):
    """
    Update a specific doctor claim channel.
    """
    instance = self.get_object()
    serializer = self.get_serializer(instance, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    self.perform_update(serializer)
    return Response(serializer.data)
    
def destroy(self, request, *args, **kwargs):
    """
    Delete a specific doctor claim channel.
    """
    instance = self.get_object()
    self.perform_destroy(instance)
    return Response(status=status.HTTP_204_NO_CONTENT)
