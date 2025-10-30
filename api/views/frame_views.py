from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from ..models import Frame, FrameStock, Branch, FrameStockHistory,FrameImage
from ..serializers import FrameSerializer, FrameStockSerializer
from django.db import transaction
from ..services.branch_protection_service import BranchProtectionsService
import json
import os
from django.db.models import Sum
from collections import defaultdict
from django.db.models import Prefetch
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
        - status: active|inactive|all - Filter frames by active status
        - init_branch_id - Filter by initial branch
        
        Required parameters (one of):
        - branch_id - Return ALL frames, but only include stock data for this branch
        - store_id - Return ONLY frames that have stock in this branch, with their stock data
        """
        status_filter = request.query_params.get("status", "active").lower()
        branch_id = request.query_params.get("branch_id")
        store_id = request.query_params.get("store_id")
        
        if not (branch_id or store_id):
            return Response(
                {"error": "Either branch_id or store_id parameter is required"},
                status=status.HTTP_400_BAD_REQUEST
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

        # Order by creation date descending (latest first)
        frames = frames.order_by('-id')

        data = []
        
        if store_id:
            # STORE_ID MODE: Only return frames that have stock in the specified branch
            # and only include stock data for that branch
            frame_ids_with_stock = FrameStock.objects.filter(
                branch_id=store_id,
            ).values_list('frame_id', flat=True).distinct()
            
            frames = frames.filter(id__in=frame_ids_with_stock)
            
            for frame in frames:               
                stocks = frame.stocks.filter(branch_id=store_id, qty__gt=0)
                frame_serializer = FrameSerializer(frame, context=self.get_serializer_context())
                frame_data = frame_serializer.data
                frame_data["stock"] = FrameStockSerializer(stocks, many=True).data
                data.append(frame_data)
                
        elif branch_id:
            # BRANCH_ID MODE: Return ALL frames, but only include stock data for the specified branch
            for frame in frames:
                stocks = frame.stocks.filter(branch_id=branch_id)
                frame_data = FrameSerializer(frame).data
                frame_data["stock"] = FrameStockSerializer(stocks, many=True).data
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
        frame_serializer = self.get_serializer(data=data, context={'request': request})
        frame_serializer.is_valid(raise_exception=True)
    
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
            stock_entry = stock_serializer.save()
            stock_entries.append(stock_entry)
            
            # Create FrameStockHistory entry for the initial stock addition
            FrameStockHistory.objects.create(
                frame=frame,
                branch=stock_entry.branch,
                action=FrameStockHistory.ADD,
                quantity_changed=stock_entry.qty
            )

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
        branch = BranchProtectionsService.validate_branch_id(request)
        frame = self.get_object()
        stock = frame.stocks.filter(branch_id=branch.id)
        frame_serializer = self.get_serializer(frame)
        frame_data = frame_serializer.data
        frame_data["stock"] = FrameStockSerializer(stock, many=True).data
        frame_data["image_url"] = frame_serializer.get_image_url(frame) if frame.image else None
        return Response(frame_data)

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        """
        Update frame details and optionally update stock details.
        Handles image updates by cleaning up old images when replaced.
        """
        frame = self.get_object()
        old_image_instance = None
        
        # Store old image instance before making any changes
        if frame.image:
            old_image_instance = frame.image
        
        if "image" in request.data and request.data["image"] is not None and request.data["image"] != "":
            # Get all frames that use the same image
            frames_using_same_image = list(Frame.objects.filter(image_id=frame.image_id).exclude(id=frame.id))

            # Create a new image for the frame
            new_image = request.data["image"]
            create_new_image = FrameImage.objects.create(image=new_image)
            
            # Update the current frame with the new image
            frame.image = create_new_image
            frame.save()
            
            # Update all frames that were using the same image
            if frames_using_same_image:
                Frame.objects.filter(id__in=[f.id for f in frames_using_same_image]).update(image=create_new_image)

            # Delete the old image if no other frames are using it
            # The FrameImage.delete() method will handle file and folder cleanup
            if old_image_instance and not Frame.objects.filter(image=old_image_instance).exists():
                old_image_instance.delete()

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
        
        updated_frame = serializer.save()
        
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
        branch_id = request.query_params.get('branch_id')
        if not branch_id:
            return Response({"error": "branch_id is required"}, status=400)

        branch_id = int(branch_id)

        # Prefetch related data including the image
        frames = Frame.objects.select_related(
            'brand', 'code', 'color', 'image'
        ).prefetch_related(
            Prefetch(
                'stocks',
                queryset=FrameStock.objects.filter(branch_id=branch_id),
                to_attr='filtered_stocks'
            )
        ).filter(is_active=True)

        # Create serializer context with request for URL building
        context = {'request': request}
        frame_serializer = FrameSerializer(context=context)

        grouped = {}

        for frame in frames:
            if not frame.filtered_stocks:
                continue  # skip frames that have no stock entry for this branch

            stock_qty = frame.filtered_stocks[0].qty  # Only one stock per frame per branch
            brand_name = frame.brand.name
            code_name = frame.code.name
            key = (brand_name, code_name)

            # Get image URL using the serializer's method
            image_url = frame_serializer.get_image_url(frame) if frame.image else None

            if key not in grouped:
                grouped[key] = {
                    "brand_name": brand_name,
                    "code_name": code_name,
                    "size": frame.size,
                    "species": frame.species,
                    "image_url": image_url,
                    "total_qty": 0,
                    "color_ids": set(),
                    "frames": []
                }

            grouped[key]["color_ids"].add(frame.color.id)
            grouped[key]["total_qty"] += stock_qty
            grouped[key]["frames"].append({
                "id": frame.id,
                "brand": frame.brand.id,
                "code": frame.code.id,
                "color": frame.color.id,
                "image": frame.image.id if frame.image else None,
                "color_name": frame.color.name,
                "price": str(frame.price),
                "size": frame.size,
                "species": frame.species,
                "brand_type": frame.get_brand_type_display(),
                "image_url": image_url,  # Use the URL from serializer
                "is_active": frame.is_active,
                "initial_branch": frame.initial_branch.id if frame.initial_branch else None,
                "stock_qty": stock_qty,
                "stock": [
                    {
                        "branch_id": stock.branch_id,
                        "qty": stock.qty
                    }
                    for stock in frame.filtered_stocks
                ]
            })

        result = []
        for group in grouped.values():
            result.append({
                "brand_name": group["brand_name"],
                "code_name": group["code_name"],
                "size": group["size"],
                "image_url": group["image_url"],
                "species": group["species"],
                "total_color": len(group["color_ids"]),
                "total_qty": group["total_qty"],
                "frames": group["frames"]
            })

        return Response(result)