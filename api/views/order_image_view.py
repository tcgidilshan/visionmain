from rest_framework import generics, status, permissions
from rest_framework.response import Response
from ..models import Order, OrderImage
from ..serializers import OrderImageSerializer

class OrderImageListCreateView(generics.ListCreateAPIView):
    queryset = OrderImage.objects.all()
    serializer_class = OrderImageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        order_id = self.request.query_params.get('order_id')
        if order_id:
            queryset = queryset.filter(order_id=order_id)
        return queryset.order_by('-uploaded_at')

    def create(self, request, *args, **kwargs):
        # Ensure order exists and user has permission
        order_id = request.data.get('order')
        if not order_id:
            return Response(
                {"error": "Order ID is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            return Response(
                {"error": "Order not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )

        # Check if the request contains an image
        if 'image' not in request.FILES:
            return Response(
                {"error": "No image file provided"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create the order image
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)