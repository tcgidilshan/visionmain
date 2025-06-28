from rest_framework import generics, filters
from rest_framework.response import Response
from ..models import FrameStockHistory, Frame
from ..serializers import FrameStockHistorySerializer

class FrameHistoryReportView(generics.ListAPIView):
    serializer_class = FrameStockHistorySerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['frame__id', 'branch__id']  # Allow searching by frame ID and branch ID

    def get_queryset(self):
        queryset = FrameStockHistory.objects.all()
        
        # Get query parameters
        frame_id = self.request.query_params.get('frame_id')
        branch_id = self.request.query_params.get('branch_id')
        
        # Apply filters if parameters are provided
        if frame_id:
            queryset = queryset.filter(frame_id=frame_id)
        if branch_id:
            queryset = queryset.filter(branch_id=branch_id)
            
        # Filter only transfer actions
        queryset = queryset.filter(action='transfer')
        
        # Order by most recent first
        return queryset.order_by('-timestamp')

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        
        # Get frame details if frame_id is provided
        frame_id = request.query_params.get('frame_id')
        branch_id = request.query_params.get('branch_id')
        
        frame_details = None
        if frame_id:
            try:
                frame = Frame.objects.get(id=frame_id)
                frame_details = {
                    'id': frame.id,
                    'brand': frame.brand.name,
                    'code': frame.code.name,
                    'color': frame.color.name,
                    'size': frame.size,
                    'species': frame.species
                }
            except Frame.DoesNotExist:
                pass
        
        # Get branch details if branch_id is provided
        branch_details = None
        if branch_id:
            try:
                from ..models import Branch
                branch = Branch.objects.get(id=branch_id)
                branch_details = {
                    'id': branch.id,
                    'name': branch.branch_name,
                    'location': branch.location
                }
            except Branch.DoesNotExist:
                pass
        
        # Paginate the queryset
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response({
                'frame': frame_details,
                'branch': branch_details,
                'transfers': serializer.data
            })
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'frame': frame_details,
            'branch': branch_details,
            'transfers': serializer.data
        })