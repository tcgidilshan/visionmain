from rest_framework import generics, status, filters
from rest_framework.response import Response
from ..models import OtherItem, OtherItemStock
from rest_framework.pagination import PageNumberPagination
from ..serializers import OtherItemSerializer, OtherItemStockSerializer

class CustomPagination(PageNumberPagination):
    """
    Custom pagination class for paginating OtherItem results.
    """
    page_size = 10  # Default items per page
    page_size_query_param = 'page_size'  # Allows dynamic page size
    max_page_size = 100  # Maximum allowed page size

class OtherItemListCreateView(generics.ListCreateAPIView):
    """
    API View to list all OtherItems with stock or create a new one.
    """
    queryset = OtherItem.objects.prefetch_related('stocks')  # Optimized query
    serializer_class = OtherItemSerializer
    pagination_class = CustomPagination  # ✅ Pagination added
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]  # ✅ Search & ordering filters added
    search_fields = ['name']  # ✅ Allows searching by item name
    ordering_fields = ['name', 'price']  # ✅ Sorting options
    ordering = ['name']  # ✅ Default ordering by name

    def list(self, request, *args, **kwargs):
        """
        List paginated OtherItems with stock data.
        """
        queryset = self.filter_queryset(self.get_queryset())  # Apply search & ordering filters
        paginated_queryset = self.paginate_queryset(queryset)

        response_data = [
            {
                "item": OtherItemSerializer(item).data,
                "stock": OtherItemStockSerializer(item.stocks.all(), many=True).data
            }
            for item in paginated_queryset
        ]

        return self.get_paginated_response(response_data) 

    def create(self, request, *args, **kwargs):
        """
        Create OtherItem with optional stock data.
        """
        other_item_serializer = OtherItemSerializer(data=request.data)
        other_item_serializer.is_valid(raise_exception=True)
        other_item = other_item_serializer.save()

        stock_data = request.data.get("stock", None)
        stock_serializer = None
        if stock_data:
            stock_data["other_item_id"] = other_item.id  # Link stock to item
            stock_serializer = OtherItemStockSerializer(data=stock_data)
            stock_serializer.is_valid(raise_exception=True)
            stock_serializer.save()

        return Response(
            {
                "message": "OtherItem created successfully",
                "item": other_item_serializer.data,
                "stock": stock_serializer.data if stock_serializer else None
            },
            status=status.HTTP_201_CREATED,
        )


class OtherItemRetrieveUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    """
    API View to retrieve, update, or delete a specific OtherItem with stock.
    """
    queryset = OtherItem.objects.prefetch_related('stocks')
    serializer_class = OtherItemSerializer

    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve an item along with stock info.
        """
        instance = self.get_object()
        stock_serializer = OtherItemStockSerializer(instance.stocks.all(), many=True)

        return Response(
            {
                "item": OtherItemSerializer(instance).data,
                "stock": stock_serializer.data
            }
        )

    def update(self, request, *args, **kwargs):
        """
        Update an item and its stock details.
        """
        instance = self.get_object()
        other_item_serializer = OtherItemSerializer(instance, data=request.data, partial=True)
        other_item_serializer.is_valid(raise_exception=True)
        other_item_serializer.save()

        stock_data = request.data.get("stock", None)
        stock_serializer = None
        if stock_data:
            stock_instance, created = OtherItemStock.objects.get_or_create(other_item=instance)
            stock_serializer = OtherItemStockSerializer(stock_instance, data=stock_data, partial=True)
            stock_serializer.is_valid(raise_exception=True)
            stock_serializer.save()

        return Response(
            {
                "message": "OtherItem and stock updated successfully",
                "item": other_item_serializer.data,
                "stock": stock_serializer.data if stock_serializer else None
            },
            status=status.HTTP_200_OK
        )

    def delete(self, request, *args, **kwargs):
        """
        Delete an item and its associated stock.
        """
        instance = self.get_object()
        instance.stocks.all().delete()  # Delete stock first
        instance.delete()

        return Response({"message": "OtherItem and its stock deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
