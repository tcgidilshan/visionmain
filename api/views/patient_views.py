from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from rest_framework.filters import SearchFilter
from ..models import Patient
from ..serializers import PatientSerializer
class PatientPagination(PageNumberPagination):
    """
    Custom Pagination for Patients
    """
    page_size = 10  # Number of records per page
    page_size_query_param = 'page_size'
    max_page_size = 100

class PatientListView(ListAPIView):
    """
    API View to List All Patients with Pagination and Search by Name or Phone
    """
    queryset = Patient.objects.all()
    serializer_class = PatientSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = PatientPagination
    filter_backends = [SearchFilter]
    search_fields = ['name', 'phone_number']  # Searchable fields
    filterset_fields = ['name', 'phone_number']

class PatientUpdateView(RetrieveUpdateAPIView):
    """
    API View to Retrieve and Update a Patient
    """
    queryset = Patient.objects.all()
    serializer_class = PatientSerializer
    permission_classes = [IsAuthenticated]
    def perform_update(self, serializer):
        """
         Check for duplicate phone_number and nic before updating automaticaly hadle from Patient Model so didnt add filter option.
        """
        phone_number = self.request.data.get("phone_number", serializer.instance.phone_number)
        nic = self.request.data.get("nic", serializer.instance.nic)

        # If no duplicates, proceed with update
        serializer.save(
            name=self.request.data.get("name", serializer.instance.name),
            phone_number=phone_number,
            nic=nic,
        )