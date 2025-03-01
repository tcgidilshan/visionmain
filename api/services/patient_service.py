from ..models import Patient,Refraction
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

        # ✅ Ensure `name` is provided
        if not patient_data.get("name"):
            raise ValueError("Patient name is required.")

        phone_number = patient_data.get("phone_number")
        name = patient_data.get("name")
        nic = patient_data.get("nic")
        refraction_id = patient_data.get("refraction_id")

         # 🔍 **Validate `refraction_id` if provided**
        if refraction_id:
            if not Refraction.objects.filter(id=refraction_id).exists():
                raise ValueError(f"Refraction ID {refraction_id} does not exist.")

        # 🔍 Check for an existing patient using both `phone_number` and `name`
        patient = Patient.objects.filter(phone_number=phone_number, name=name).first()

        if patient:  # ✅ Existing patient found → Update details
            patient.address = patient_data.get("address", patient.address)
            patient.date_of_birth = patient_data.get("date_of_birth", patient.date_of_birth)
            if "refraction_id" in patient_data:
                patient.refraction_id = patient_data["refraction_id"]
            if nic:  # ✅ Update NIC if newly provided
                patient.nic = nic
            patient.save()
        
        else:  # ❌ No existing patient found → Create a new one
            patient = Patient.objects.create(
                name=name,
                phone_number=phone_number,
                address=patient_data.get("address"),
                date_of_birth=patient_data.get("date_of_birth"),
                refraction_id=patient_data.get("refraction_id"),
                nic=nic  # Store NIC if provided
            )

        return patient
