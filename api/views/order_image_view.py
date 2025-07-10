from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.exceptions import NotFound, PermissionDenied
from ..models import Order, OrderImage
from ..serializers import OrderImageSerializer

class OrderImageListCreateView(generics.ListCreateAPIView):
    """
    View for listing and creating order images
    """
    serializer_class = OrderImageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Get all images for a specific order
        """
        order_id = self.kwargs.get('order_id')
        return OrderImage.objects.filter(order_id=order_id).order_by('-uploaded_at')

    def get_order_or_404(self, order_id):
        """
        Helper method to get order or return 404
        """
        try:
            return Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            raise NotFound(detail="Order not found")

    def perform_create(self, serializer):
        """
        Create a new image for the specified order
        """
        order_id = self.kwargs.get('order_id')
        order = self.get_order_or_404(order_id)
        serializer.save(order=order)

    def create(self, request, *args, **kwargs):
        """
        Handle image upload for an order
        """
        # Check if the request contains an image
        if 'image' not in request.FILES:
            return Response(
                {"error": "No image file provided"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get the order ID from URL
        order_id = self.kwargs.get('order_id')
        try:
            order = self.get_order_or_404(order_id)
        except NotFound as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_404_NOT_FOUND
            )

        # Add order to request data
        request.data['order'] = order.id
        
        return super().create(request, *args, **kwargs)

    def list(self, request, *args, **kwargs):
        """
        List all images for an order
        """
        try:
            self.get_order_or_404(self.kwargs.get('order_id'))
            return super().list(request, *args, **kwargs)
        except NotFound as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_404_NOT_FOUND
            )

    def get_object(self):
        """
        Get the order image or return 404
        """
        order_id = self.kwargs.get('order_id')
        image_id = self.kwargs.get('pk')
        
        try:
            # Verify the order exists and the image belongs to it
            self.get_order_or_404(order_id)
            image = OrderImage.objects.get(id=image_id, order_id=order_id)
            return image
        except OrderImage.DoesNotExist:
            raise NotFound(detail="Image not found for this order")

class OrderImageDetailView(generics.RetrieveDestroyAPIView):
    """
    View for retrieving and deleting a single order image
    """
    serializer_class = OrderImageSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_url_kwarg = 'pk'

    def get_queryset(self):
        """
        Get the queryset filtered by order_id
        """
        order_id = self.kwargs.get('order_id')
        return OrderImage.objects.filter(order_id=order_id)

    def get_object(self):
        """
        Get the order image or return 404
        """
        queryset = self.filter_queryset(self.get_queryset())
        obj = generics.get_object_or_404(queryset, pk=self.kwargs['pk'])
        return obj

    def destroy(self, request, *args, **kwargs):
        """
        Delete an order image
        """
        try:
            print(f"[DEBUG] Attempting to delete image with kwargs: {kwargs}")
            instance = self.get_object()
            print(f"[DEBUG] Found instance: {instance}")
            print(f"[DEBUG] Image path: {instance.image.path if instance.image else 'No image'}")
            
            self.perform_destroy(instance)
            print("[DEBUG] Image deletion completed successfully")
            
            return Response(
                {"message": "Image deleted successfully"}, 
                status=status.HTTP_204_NO_CONTENT
            )
        except Exception as e:
            print(f"[ERROR] Failed to delete image: {str(e)}")
            import traceback
            print(f"[DEBUG] Traceback: {traceback.format_exc()}")
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    def perform_destroy(self, instance):
        """
        Perform the actual deletion of the image file and database record
        """
        import os
        from django.conf import settings
        
        # Store the file path before deletion
        file_path = instance.image.path if instance.image else None
        
        # Delete the image file from storage
        if instance.image:
            print(f"[DEBUG] Deleting file: {file_path}")
            print(f"[DEBUG] File exists before deletion: {os.path.exists(file_path) if file_path else 'No file path'}")
            
            try:
                # First try the model's delete method
                instance.image.delete(save=False)
                print("[DEBUG] File deleted successfully using model's delete method")
            except Exception as e:
                
                if hasattr(instance.image, 'storage') and hasattr(instance.image, 'name'):
                    try:
                        # Try direct storage deletion
                        instance.image.storage.delete(instance.image.name)
                        print("[DEBUG] File deleted successfully using storage directly")
                    except Exception as e2:
                        print(f"[WARNING] Failed to delete using storage directly: {e2}")
                        try:
                            # Last resort: try direct file system deletion
                            if file_path and os.path.exists(file_path):
                                os.remove(file_path)
                                print("[DEBUG] File deleted successfully using os.remove")
                        except Exception as e3:
                            print(f"[ERROR] All deletion methods failed: {e3}")
                            raise
        
        # Delete the empty directory if it exists
        if file_path:
            try:
                directory = os.path.dirname(file_path)
                media_root = settings.MEDIA_ROOT
                
                # Only delete if the directory is within MEDIA_ROOT and is empty
                if (directory.startswith(media_root) and 
                    os.path.exists(directory) and 
                    not os.listdir(directory)):
                    os.rmdir(directory)
                    print(f"[DEBUG] Deleted empty directory: {directory}")
                elif os.path.exists(directory):
                    print(f"[DEBUG] Directory not empty, not deleting: {directory}")
                else:
                    print("[DEBUG] Directory already deleted")
            except Exception as e:
                print(f"[WARNING] Could not delete directory: {e}")
        
        # Delete the database record
        instance.delete()
   