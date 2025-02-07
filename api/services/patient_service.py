from ..models import Patient
from ..serializers import PatientSerializer

class PatientService:
    """
    Service class to handle patient creation and updating.
    """

    @staticmethod
    def create_or_update_patient(patient_data):
        """
        Creates or updates a patient based on provided data.
        Returns the patient instance.
        """
        patient, created = Patient.objects.get_or_create(
            nic=patient_data.get("nic"),  # Unique NIC check
            defaults={
                "name": patient_data.get("name"),
                "phone_number": patient_data.get("phone_number"),
                "address": patient_data.get("address"),
                "date_of_birth": patient_data.get("date_of_birth"),
                "refraction_id": patient_data.get("refraction_id")
            },
        )

        if not created:  # If patient exists, update their details
            patient.name = patient_data.get("name", patient.name)
            patient.phone_number = patient_data.get("phone_number", patient.phone_number)
            patient.address = patient_data.get("address", patient.address)
            patient.date_of_birth = patient_data.get("date_of_birth", patient.date_of_birth)

             # ✅ Update `refraction_id` only if provided
            if "refraction_id" in patient_data:
                patient.refraction_id = patient_data["refraction_id"]
                
            patient.save()

        return patient
