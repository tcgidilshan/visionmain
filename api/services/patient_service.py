from ..models import Patient,Refraction
from ..serializers import PatientSerializer

class PatientService:
    """
    Service class to handle patient creation and updating.
    """

    @staticmethod
    def create_or_update_patient(patient_data):
        """
        Creates or updates a patient based on NIC (priority) or phone+name.
        """

        if not patient_data.get("name"):
            raise ValueError("Patient name is required.")

        phone_number = patient_data.get("phone_number")
        nic = patient_data.get("nic")
        name = patient_data.get("name")
        refraction_id = patient_data.get("refraction_id")

        # 🔍 Validate refraction if provided
        if refraction_id and not Refraction.objects.filter(id=refraction_id).exists():
            raise ValueError(f"Refraction ID {refraction_id} does not exist.")

        patient = None

        # 🔐 Priority 1: Match by NIC
        if nic:
            patient = Patient.objects.filter(nic=nic).first()

        # 🔐 Priority 2: Match by phone + name (only if NIC not matched)
        if not patient and phone_number and name:
            patient = Patient.objects.filter(phone_number=phone_number, name=name).first()

        if patient:
            # ✅ Update patient
            for field in ["address", "date_of_birth", "phone_number", "nic", "refraction_id", "patient_note"]:
                if field in patient_data and patient_data[field] is not None:
                    setattr(patient, field, patient_data[field])
            patient.save()
            return patient

        # 🔒 Check for conflicting phone/NIC (not tied to this name)
        if phone_number and Patient.objects.filter(phone_number=phone_number).exists():
            raise ValueError("Another patient already exists with this phone number.")

        if nic and Patient.objects.filter(nic=nic).exists():
            raise ValueError("Another patient already exists with this NIC.")

        # ➕ Create new patient
        return Patient.objects.create(
            name=name,
            phone_number=phone_number,
            address=patient_data.get("address"),
            date_of_birth=patient_data.get("date_of_birth"),
            refraction_id=refraction_id,
            nic=nic,
            patient_note=patient_data.get("patient_note")
        )