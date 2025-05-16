from ..models import Patient,Refraction
from ..serializers import PatientSerializer

class PatientService:
    """
    Service class to handle patient creation and updating.
    """

    @staticmethod
    def create_or_update_patient(patient_data):
        """
        Creates or updates a patient based on NIC (preferred), or phone_number + name combo.
        """

        if not patient_data.get("name"):
            raise ValueError("Patient name is required.")

        name = patient_data.get("name")
        phone_number = patient_data.get("phone_number")
        nic = patient_data.get("nic")
        refraction_id = patient_data.get("refraction_id")

        # 🔍 Validate refraction_id if provided
        if refraction_id and not Refraction.objects.filter(id=refraction_id).exists():
            raise ValueError(f"Refraction ID {refraction_id} does not exist.")

        patient = None

        # 🔐 Step 1: Match by NIC if present
        if nic:
            patient = Patient.objects.filter(nic=nic).first()

        # 🔐 Step 2: If no NIC match, try phone + name
        if not patient and phone_number and name:
            patient = Patient.objects.filter(phone_number=phone_number, name=name).first()

        if patient:
            # ✅ Update existing patient
            for field in ["name", "phone_number", "address", "date_of_birth", "refraction_id", "patient_note", "nic"]:
                if field in patient_data and patient_data[field] is not None:
                    setattr(patient, field, patient_data[field])
            patient.save()
            return patient

        # ➕ Step 3: Create new patient
        return Patient.objects.create(
            name=name,
            phone_number=phone_number,
            address=patient_data.get("address"),
            date_of_birth=patient_data.get("date_of_birth"),
            refraction_id=refraction_id,
            nic=nic,
            patient_note=patient_data.get("patient_note")
        )
