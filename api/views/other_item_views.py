from rest_framework import generics, status, filters
from rest_framework.response import Response
from ..models import OtherItem, OtherItemStock
from rest_framework.pagination import PageNumberPagination
from ..serializers import OtherItemSerializer, OtherItemStockSerializer
from rest_framework.exceptions import ValidationError
from ..services.branch_protection_service import BranchProtectionsService
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
        queryset = self.filter_queryset(self.get_queryset())
        
        # Filter by is_active: default to active items, filter to inactive if param is 'false'
        is_active_param = request.GET.get('is_active')
        if is_active_param is None:
            queryset = queryset.filter(is_active=True)
        elif is_active_param.lower() == 'false':
            queryset = queryset.filter(is_active=False)
        
        branch = BranchProtectionsService.validate_branch_id(request)
        paginated_queryset = self.paginate_queryset(queryset)

        response_data = [
            {
                "item": OtherItemSerializer(item).data,
                "stock": OtherItemStockSerializer(item.stocks.filter(branch_id=branch.id), many=True).data
            }
            for item in paginated_queryset
        ]

        return self.get_paginated_response(response_data) 

    def create(self, request, *args, **kwargs):
        """
        Create OtherItem with stock data for multiple branches (if provided).
        """
        other_item_serializer = OtherItemSerializer(data=request.data)
        other_item_serializer.is_valid(raise_exception=True)
        other_item = other_item_serializer.save()

        # Check if stock data is provided
        stock_data_list = request.data.get("stock", [])
        stock_serializers = []  # List to hold stock serializers

        if stock_data_list:
            for stock_data in stock_data_list:
                # Ensure branch_id is provided for stock creation
                branch_id = stock_data.get("branch_id")
                if not branch_id:
                    return Response(
                        {"error": "Branch ID is required for stock creation."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                stock_data["other_item_id"] = other_item.id  # Link stock to item
                stock_serializer = OtherItemStockSerializer(data=stock_data)
                stock_serializer.is_valid(raise_exception=True)
                stock_serializer.save()
                stock_serializers.append(stock_serializer)

        return Response(
            {
                "message": "OtherItem created successfully",
                "item": other_item_serializer.data,
                "stock": [serializer.data for serializer in stock_serializers]
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
        branch=BranchProtectionsService.validate_branch_id(request)
        stock_serializer = OtherItemStockSerializer(instance.stocks.filter(branch_id=branch.id), many=True)

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

        other_item = self.get_object()
        other_item_serializer = self.get_serializer(other_item, data=request.data.get("item",{}), partial=True)
        other_item_serializer.is_valid(raise_exception=True)
        other_item_serializer.save()

        stock_data_list = request.data.get("stock", [])
        updated_stocks = []

        if isinstance(stock_data_list, list):
            for stock_data in stock_data_list:
                if "initial_count" not in stock_data:
                    return Response(
                        {"error": "initial_count is required for all stock entries."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                branch_id = stock_data.get("branch_id")
                if not branch_id:
                    return Response(
                        {"error": "branch_id is required for stock updates."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                # ✅ Check if stock exists for this lens + branch
                stock_instance = other_item.stocks.filter(branch_id=branch_id).first()
                stock_data["item"] = other_item.id  # Link stock to item
                if stock_instance:
                    stock_serializer = OtherItemStockSerializer(stock_instance, data=stock_data, partial=True)
                else:
                    stock_serializer = OtherItemStockSerializer(data=stock_data)
                
                stock_serializer.is_valid(raise_exception=True)
                updated_stocks.append(stock_serializer.save())
               
        return Response(
            {
                "message": "OtherItem and stock updated successfully",
                "item": other_item_serializer.data,
                "stock": OtherItemStockSerializer(updated_stocks, many=True).data  # ✅ Return updated stock list
            },
            status=status.HTTP_200_OK
        )

    def delete(self, request, *args, **kwargs):
        """
        Soft delete an item by setting is_active to False.
        """
        instance = self.get_object()
        instance.is_active = False
        instance.save()

        return Response({"message": "OtherItem soft deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
