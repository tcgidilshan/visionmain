from rest_framework import generics, status
from rest_framework.response import Response
from ..models import Doctor
from ..serializers import DoctorSerializer


class DoctorListCreateView(generics.ListCreateAPIView):
    """
    Handles listing all doctors and creating a new doctor.
    """
    queryset = Doctor.objects.all()
    serializer_class = DoctorSerializer

    def list(self, request, *args, **kwargs):
        """
        List all doctors with optional filtering (e.g., by status or specialization).
        """
        queryset = self.get_queryset()

        # Optional filtering by status or specialization
        status_filter = request.query_params.get('status')
        specialization_filter = request.query_params.get('specialization')

        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if specialization_filter:
            queryset = queryset.filter(specialization__icontains=specialization_filter)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        """
        Create a new doctor entry.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class DoctorRetrieveUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    """
    Handles retrieving, updating, and deleting a doctor by ID.
    """
    queryset = Doctor.objects.all()
    serializer_class = DoctorSerializer

    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve a doctor by ID.
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        """
        Update an existing doctor (partial or full).
        """
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        """
        Delete a doctor by ID.
        """
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)
