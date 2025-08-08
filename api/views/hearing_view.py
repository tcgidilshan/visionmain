from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework import filters
from ..models import HearingItem, HearingItemStock
from ..serializers import HearingItemSerializer, HearingItemStockSerializer
from ..services.branch_protection_service import BranchProtectionsService
from ..services.pagination_service import PaginationService

class HearingItemListCreateView(generics.ListCreateAPIView):
    """
    API View to list all HearingItems with stock or create a new one.
    """
    queryset = HearingItem.objects.prefetch_related('stocks')
    serializer_class = HearingItemSerializer
    pagination_class = PaginationService
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'code']
    ordering_fields = ['name', 'price', 'code']
    ordering = ['name']

    def list(self, request, *args, **kwargs):
        """
        List paginated HearingItems with stock data.
        By default, only active items are returned. To include inactive items,
        add ?is_active=false to the request.
        """
        # Get the base queryset
        queryset = self.get_queryset()
        
        # Check if is_active filter is explicitly provided in the request
        is_active_param = request.query_params.get('is_active')
        if is_active_param is not None:
            # Convert string parameter to boolean
            is_active = is_active_param.lower() == 'true'
            queryset = queryset.filter(is_active=is_active)
        else:
            # Default to only active items if not specified
            queryset = queryset.filter(is_active=True)
        
        # Apply search and ordering filters
        queryset = self.filter_queryset(queryset)
        
        # Get the branch and paginate
        branch = BranchProtectionsService.validate_branch_id(request)
        paginated_queryset = self.paginate_queryset(queryset)

        response_data = [
            {
                "item": HearingItemSerializer(item).data,
                "stock": HearingItemStockSerializer(item.stocks.filter(branch_id=branch.id), many=True).data
            }
            for item in paginated_queryset
        ]

        return self.get_paginated_response(response_data)

    def create(self, request, *args, **kwargs):
        """
        Create HearingItem with stock data for multiple branches (if provided).
        """
        hearing_item_serializer = HearingItemSerializer(data=request.data)
        hearing_item_serializer.is_valid(raise_exception=True)
        hearing_item = hearing_item_serializer.save()

        # Check if stock data is provided
        stock_data_list = request.data.get("stock", [])
        stock_serializers = []

        if stock_data_list:
            for stock_data in stock_data_list:
                # Ensure branch_id is provided for stock creation
                branch_id = stock_data.get("branch_id")
                if not branch_id:
                    return Response(
                        {"error": "Branch ID is required for stock creation."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                stock_data["hearing_item_id"] = hearing_item.id
                stock_serializer = HearingItemStockSerializer(data=stock_data)
                stock_serializer.is_valid(raise_exception=True)
                stock_serializer.save()
                stock_serializers.append(stock_serializer)

        return Response(
            {
                "message": "HearingItem created successfully",
                "item": hearing_item_serializer.data,
                "stock": [serializer.data for serializer in stock_serializers]
            },
            status=status.HTTP_201_CREATED,
        )


class HearingItemRetrieveUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    """
    API View to retrieve, update, or delete a specific HearingItem with stock.
    """
    queryset = HearingItem.objects.prefetch_related('stocks')
    serializer_class = HearingItemSerializer

    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve a HearingItem along with its stock information.
        """
        instance = self.get_object()
        branch = BranchProtectionsService.validate_branch_id(request)
        stock_serializer = HearingItemStockSerializer(
            instance.stocks.filter(branch_id=branch.id), 
            many=True
        )

        return Response({
            "item": HearingItemSerializer(instance).data,
            "stock": stock_serializer.data
        })

    def update(self, request, *args, **kwargs):
        """
        Update a HearingItem and its stock information.
        """
        hearing_item = self.get_object()
        
        # Update the HearingItem
        item_serializer = self.get_serializer(
            hearing_item, 
            data=request.data.get("item", {}), 
            partial=True
        )
        item_serializer.is_valid(raise_exception=True)
        item_serializer.save()

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
                
                # Check if stock exists for this hearing item + branch
                stock_instance = hearing_item.stocks.filter(branch_id=branch_id).first()
                stock_data["hearing_item_id"] = hearing_item.id  # Link stock to item
                
                if stock_instance:
                    stock_serializer = HearingItemStockSerializer(
                        stock_instance, 
                        data=stock_data, 
                        partial=True
                    )
                else:
                    stock_serializer = HearingItemStockSerializer(data=stock_data)
                
                stock_serializer.is_valid(raise_exception=True)
                updated_stocks.append(stock_serializer.save())

        return Response({
            "message": "HearingItem and stock updated successfully",
            "item": item_serializer.data,
            "stock": HearingItemStockSerializer(updated_stocks, many=True).data
        }, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        """
        Soft delete a HearingItem by marking it as inactive.
        """
        instance = self.get_object()
        instance.is_active = False
        instance.save()
        return Response(
            {"message": "HearingItem has been marked as inactive"},
            status=status.HTTP_200_OK
        )