from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.exceptions import NotFound
from ..models import Order, OrderImage
from ..serializers import OrderImageSerializer

class OrderImageListCreateView(generics.ListCreateAPIView):
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