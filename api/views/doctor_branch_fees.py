#doctor branch fees CRUD
from rest_framework import generics,status
from rest_framework.response import Response
from ..models import DoctorBranchChannelFees
from ..serializers import DoctorBranchChannelFeesSerializer

##create 
class DoctorBranchChannelFeesCreateView(generics.CreateAPIView):
    queryset = DoctorBranchChannelFees.objects.all()
    serializer_class = DoctorBranchChannelFeesSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            # Check if a record with the same doctor and branch already exists
            doctor_id = request.data.get('doctor')
            branch_id = request.data.get('branch')
            if DoctorBranchChannelFees.objects.filter(doctor_id=doctor_id, branch_id=branch_id).exists():
                return Response(
                    {"error": "A record with this doctor and branch combination already exists."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

##list with branch_id,doctor_id params
class DoctorBranchChannelFeesListView(generics.ListAPIView):
    serializer_class = DoctorBranchChannelFeesSerializer
    
    def get_queryset(self):
        queryset = DoctorBranchChannelFees.objects.all()
        branch_id = self.request.query_params.get('branch_id')
        doctor_id = self.request.query_params.get('doctor_id')
        
        if branch_id:
            queryset = queryset.filter(branch_id=branch_id)
        if doctor_id:
            queryset = queryset.filter(doctor_id=doctor_id)
            
        return queryset

##update
class DoctorBranchChannelFeesUpdateView(generics.UpdateAPIView):
    queryset = DoctorBranchChannelFees.objects.all()
    serializer_class = DoctorBranchChannelFeesSerializer
    lookup_field = 'pk'  # Changed from 'id' to 'pk' for consistency with DRF
    
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        if serializer.is_valid():
            # Check if updating would create a duplicate record
            doctor_id = request.data.get('doctor', instance.doctor_id)
            branch_id = request.data.get('branch', instance.branch_id)
            if (str(doctor_id) != str(instance.doctor_id) or str(branch_id) != str(instance.branch_id)) and \
               DoctorBranchChannelFees.objects.filter(doctor_id=doctor_id, branch_id=branch_id).exists():
                return Response(
                    {"error": "A record with this doctor and branch combination already exists."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            self.perform_update(serializer)
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
