from rest_framework import generics, status
from rest_framework.response import Response
from django.db.models import Q
from ..models import ExternalLens
from ..serializers import ExternalLensSerializer

class ExternalLensListCreateView(generics.ListCreateAPIView):
    """
    Handles listing and creating external lenses with dynamic multi-filtering.
    """
    queryset = ExternalLens.objects.select_related('lens_type', 'coating', 'brand')
    serializer_class = ExternalLensSerializer

    def list(self, request, *args, **kwargs):
        queryset = ExternalLens.objects.filter(is_active=True)
        # Filters from query params
        lens_type = request.query_params.get('lens_type')
        coating = request.query_params.get('coating')
        branded = request.query_params.get('branded')
        brand = request.query_params.get('brand')

        if lens_type:
            queryset = queryset.filter(lens_type_id=lens_type)
        if coating:
            queryset = queryset.filter(coating_id=coating)
        if branded:
            queryset = queryset.filter(branded=branded)
        if brand:
            queryset = queryset.filter(brand_id=brand)

        # Dynamic dropdown filters for the frontend
        available_filters = {
            "lens_types": list(queryset.values_list("lens_type_id", flat=True).distinct()),
            "coatings": list(queryset.values_list("coating_id", flat=True).distinct()),
            "branded": list(queryset.values_list("branded", flat=True).distinct()),
            "brands": list(queryset.values_list("brand_id", flat=True).distinct()),
        }

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response({
                "results": serializer.data,
                "available_filters": available_filters
            })

        serializer = self.get_serializer(queryset, many=True)
        return Response({
            "results": serializer.data,
            "available_filters": available_filters
        })

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            self.perform_create(serializer)
        except IntegrityError:
            return Response(
                {"error": "This lens combination already exists."},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ExternalLensRetrieveUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    """
    Handles retrieving, updating, and deleting an external lens by ID.
    """
    queryset = ExternalLens.objects.select_related('lens_type', 'coating', 'brand')
    serializer_class = ExternalLensSerializer
    lookup_field = 'id'

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        try:
            self.perform_update(serializer)
        except IntegrityError:
            return Response(
                {"error": "This lens combination already exists."},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):    
        External_lens = self.get_object()
        External_lens.is_active = False
        External_lens.save()
        return Response(status=status.HTTP_204_NO_CONTENT)
