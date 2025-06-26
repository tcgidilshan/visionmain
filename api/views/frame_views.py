from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from ..models import Frame, FrameStock, Branch, FrameStockHistory
from ..serializers import FrameSerializer, FrameStockSerializer
from django.db import transaction
from ..services.branch_protection_service import BranchProtectionsService
import json
import os
from django.db.models import Sum

# List and Create Frames (with stock)
class FrameListCreateView(generics.ListCreateAPIView):
    queryset = Frame.objects.all()
    serializer_class = FrameSerializer
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
    
    def get_queryset(self):
        queryset = super().get_queryset()
        init_branch_id = self.request.query_params.get('init_branch_id')
        if init_branch_id:
            queryset = queryset.filter(branch_id=init_branch_id)
        return queryset
    
    def list(self, request, *args, **kwargs):
        """
        List frames with optional filters:
        - status: active|inactive|all
        - init_branch_id: filter by initial branch
        - branch_id: filter stock by branch
        """
        status_filter = request.query_params.get("status", "active").lower()
        branch_id = request.query_params.get("branch_id")
        
        if not branch_id:
            return Response(
                {"error": "branch_id parameter is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            branch = Branch.objects.get(id=branch_id)
        except Branch.DoesNotExist:
            return Response(
                {"error": "Branch not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        frames = self.get_queryset()
        
        # Apply status filter if provided
        if status_filter == "active":
            frames = frames.filter(is_active=True)
        elif status_filter == "inactive":
            frames = frames.filter(is_active=False)
        elif status_filter != "all":
            return Response(
                {"error": "Invalid status filter. Use 'active', 'inactive', or 'all'."},
                status=status.HTTP_400_BAD_REQUEST
            )

        data = []
        for frame in frames:
            stocks = frame.stocks.filter(branch_id=branch.id)  # Get all stock entries for this frame
            stock_data = FrameStockSerializer(stocks, many=True).data  # Ensure many=True

            frame_data = FrameSerializer(frame).data
            frame_data["stock"] = stock_data  # Store all stock records as a list

            data.append(frame_data)

        return Response(data, status=status.HTTP_200_OK)

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """
        Create a frame and add stock from JSON string array.
        Handles both with and without image upload.
        """
        # Make a mutable copy of request data
        data = request.data.copy()
        
        # Set default is_active to True if not provided
        if 'is_active' not in data:
            data['is_active'] = True

        # Handle stock data which is sent as a JSON string
        stock_data = data.get("stock")
        if stock_data:
            try:
                if isinstance(stock_data, str):
                    stock_data = json.loads(stock_data)
                # Ensure stock_data is a list
                stock_data_list = stock_data if isinstance(stock_data, list) else [stock_data] if stock_data else []
                # Update the mutable copy
                data["stock"] = stock_data_list
            except json.JSONDecodeError:
                return Response(
                    {"error": "Invalid stock data format. Must be a valid JSON array."},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            stock_data_list = []

        # Create the frame using the mutable copy
        frame_serializer = self.get_serializer(data=data)
        frame_serializer.is_valid(raise_exception=True)
        frame = frame_serializer.save()
        
        stock_entries = []

        # Process stock data
        for stock_item in stock_data_list:
            if not isinstance(stock_item, dict) or "initial_count" not in stock_item:
                return Response(
                    {"error": "Each stock entry must be an object with 'initial_count'."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            
            # Prepare stock data
            stock_item["frame"] = frame.id
            if "qty" not in stock_item:
                stock_item["qty"] = stock_item["initial_count"]
            
            stock_serializer = FrameStockSerializer(data=stock_item)
            stock_serializer.is_valid(raise_exception=True)
            stock_entries.append(stock_serializer.save())

        # Prepare response
        response_data = frame_serializer.data
        response_data["stocks"] = FrameStockSerializer(stock_entries, many=True).data
        
        return Response(response_data, status=status.HTTP_201_CREATED)

# Retrieve, Update, and Delete Frames (with stock details)
class FrameRetrieveUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Frame.objects.all()
    serializer_class = FrameSerializer
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve a frame along with its stock details.
        """
        branch=BranchProtectionsService.validate_branch_id(request)
        frame = self.get_object()
        stock = frame.stocks.filter(branch_id=branch.id)
        frame_data = FrameSerializer(frame).data
        frame_data["stock"] = FrameStockSerializer(stock, many=True).data 
        return Response(frame_data)

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        """
        Update frame details and optionally update stock details.
        Handles image updates by cleaning up old images when replaced.
        """
        frame = self.get_object()
        old_image = frame.image.path if frame.image and hasattr(frame.image, 'path') else None
        old_image_relative = str(frame.image) if frame.image else None
        
        # Handle stock data which might be a JSON string
        stock_data = request.data.get("stock")
        if stock_data and isinstance(stock_data, str):
            try:
                stock_data = json.loads(stock_data)
                if not isinstance(stock_data, list):
                    stock_data = [stock_data]
                request.data._mutable = True
                request.data["stock"] = stock_data
                request.data._mutable = False
            except json.JSONDecodeError:
                return Response(
                    {"error": "Invalid stock data format. Must be a valid JSON array."},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Process the update
        serializer = self.get_serializer(frame, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        
        try:
            updated_frame = serializer.save()
            
            # Handle image cleanup if a new image was uploaded
            if 'image' in request.data and old_image:
                try:
                    # Delete old image file if it exists
                    if os.path.exists(old_image):
                        os.remove(old_image)
                        # Try to remove the directory if it's empty
                        try:
                            os.rmdir(os.path.dirname(old_image))
                        except OSError:
                            pass  # Directory not empty, that's fine
                except Exception as e:
                    # Log the error but don't fail the request
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Error deleting old image {old_image}: {str(e)}")
            
            # Handle stock updates
            stock_entries = []
            stock_data_list = request.data.get("stock", [])
            
            if stock_data_list and isinstance(stock_data_list, list):
                for stock_item in stock_data_list:
                    if not isinstance(stock_item, dict) or "initial_count" not in stock_item:
                        return Response(
                            {"error": "Each stock entry must be an object with 'initial_count'."},
                            status=status.HTTP_400_BAD_REQUEST,
                        )

                    branch_id = stock_item.get("branch_id")
                    if not branch_id:
                        return Response(
                            {"error": "branch_id is required for stock updates."},
                            status=status.HTTP_400_BAD_REQUEST,
                        )

                    # Check if stock entry exists for the frame & branch
                    stock_instance = frame.stocks.filter(branch_id=branch_id).first()
                    old_qty = stock_instance.qty if stock_instance else 0
                    new_qty = stock_item.get('qty', old_qty)

                    

                    if stock_instance:
                        # Update existing stock
                        stock_serializer = FrameStockSerializer(stock_instance, data=stock_item, partial=True)
                    else:
                        # Create new stock entry if it doesn't exist
                        stock_item["frame"] = frame.id
                        stock_serializer = FrameStockSerializer(data=stock_item)

                    stock_serializer.is_valid(raise_exception=True)
                    updated_stock = stock_serializer.save()
                    stock_entries.append(updated_stock)
                    
                    # Create stock history record if quantity changed
                    qty_difference = updated_stock.qty - old_qty
                    
                    if qty_difference != 0:
                        action = FrameStockHistory.ADD if qty_difference > 0 else FrameStockHistory.REMOVE
                        FrameStockHistory.objects.create(
                            frame=frame,
                            branch_id=branch_id,
                            action=action,
                            quantity_changed=abs(qty_difference)
                        )

            # Prepare response
            response_data = serializer.data
            response_data["stocks"] = FrameStockSerializer(stock_entries, many=True).data if stock_entries else []
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            # If anything fails, make sure to clean up any partially uploaded file
            if 'image' in request.data and frame.image and frame.image != old_image_relative:
                try:
                    if hasattr(frame.image, 'path') and os.path.exists(frame.image.path):
                        os.remove(frame.image.path)
                except:
                    pass
            raise

    def destroy(self, request, *args, **kwargs):
        """
        Soft delete: Mark the frame as inactive instead of deleting it.
        """
        frame = self.get_object()
        frame.is_active = False
        frame.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

class FrameFilterView(APIView):
    def get(self, request):
        branch_id = request.query_params.get("branch_id")

        # You can fetch frames and manually group by brand/code/color
        frames = Frame.objects.filter(is_active=True).select_related("brand", "code", "color").prefetch_related("stocks")

        grouped = {}
        for frame in frames:
            key = (frame.brand.id, frame.code.id, frame.color.name, frame.size, frame.species)
            if key not in grouped:
                grouped[key] = {
                    "brand": frame.brand.name,
                    "brand_id": frame.brand.id,
                    "code": frame.code.name,
                    "code_id": frame.code.id,
                    "color_name": frame.color.name,
                    "size": frame.size,
                    "species": frame.species,
                    "price": float(frame.price),
                    "total_qty": 0,
                    "frames": [],
                }

            stock_qs = frame.stocks.filter(branch_id=branch_id) if branch_id else frame.stocks.all()
            stock_list = [
                {
                    "qty": s.qty,
                    "initial_count": s.initial_count,
                    "limit": s.limit,
                    "branch_id": s.branch_id
                }
                for s in stock_qs
            ]

            total_qty = sum(s["qty"] for s in stock_list if s)

            grouped[key]["total_qty"] += total_qty
            grouped[key]["frames"].append({
                "id": frame.id,
                "brand": frame.brand.id,
                "brand_name": frame.brand.name,
                "code": frame.code.id,
                "code_name": frame.code.name,
                "color": frame.color.id,
                "color_name": frame.color.name,
                "price": str(frame.price),
                "size": frame.size,
                "species": frame.species,
                "image": frame.image.url if frame.image else None,
                "image_url": frame.image.url if frame.image else None,
                "brand_type": frame.brand_type,
                "brand_type_display": frame.get_brand_type_display(),
                "is_active": frame.is_active,
                "stock": stock_list
            })

        return Response(list(grouped.values()))