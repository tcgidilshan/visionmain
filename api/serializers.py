from rest_framework import serializers
from .models import (
    Branch,
    Refraction,
    RefractionDetails,
    Brand,
    Color,
    Code,
    Frame,
    FrameStock,
    LenseType,
    Coating,
    Lens,
    LensStock,
    Power,
    LensPower,
    LensCleaner,
    LensCleanerStock,
    Order,
    OrderItem,
    OrderPayment,
    Doctor,
    Patient,
    Schedule,
    Appointment,
    ChannelPayment
)

class BranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = '__all__'
        
class RefractionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Refraction
        fields = ['id', 'customer_full_name', 'customer_mobile', 'refraction_number']
        read_only_fields = ['refraction_number']  # Auto-generated

class RefractionDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = RefractionDetails
        fields = [
            'id', 
            'refraction',  # ForeignKey to Refraction
            'hb_rx_right_dist', 
            'hb_rx_left_dist',
            'hb_rx_right_near',
            'hb_rx_left_near',
            'auto_ref_right',
            'auto_ref_left',
            'ntc_right',
            'ntc_left',
            'va_without_glass_right',
            'va_without_glass_left',
            'va_without_ph_right',
            'va_without_ph_left',
            'va_with_glass_right',
            'va_with_glass_left',
            'right_eye_dist_sph',
            'right_eye_dist_cyl',
            'right_eye_dist_axis',
            'right_eye_near_sph',
            'left_eye_dist_sph',
            'left_eye_dist_cyl',
            'left_eye_dist_axis',
            'left_eye_near_sph',
            'remark'
        ]
  
class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ['id', 'name']

class ColorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Color
        fields = ['id', 'name']
        
class CodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Code
        fields = ['id', 'name', 'brand']
        
class FrameSerializer(serializers.ModelSerializer):
    class Meta:
        model = Frame
        fields = [
            'id',
            'brand',
            'code',
            'color',
            'price',
            'size',
            'species',
            'image',
        ]
        
class FrameStockSerializer(serializers.ModelSerializer):
    class Meta:
        model = FrameStock
        fields = ['id', 'frame', 'qty', 'initial_count']
        
class LenseTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LenseType
        fields = ['id', 'name', 'description']
        
class CoatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coating
        fields = ['id', 'name', 'description']
        
class LensSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lens
        fields = ['id', 'type', 'coating', 'price']
        
class LensStockSerializer(serializers.ModelSerializer):
    class Meta:
        model = LensStock
        fields = ['id', 'lens', 'initial_count', 'qty']
        
class PowerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Power
        fields = ['id', 'name', 'side']
        
class LensPowerSerializer(serializers.ModelSerializer):
    class Meta:
        model = LensPower
        fields = ['id', 'lens', 'power', 'value', 'side']
        
class LensCleanerSerializer(serializers.ModelSerializer):
    class Meta:
        model = LensCleaner
        fields = ['id', 'name', 'price']
        
class LensCleanerStockSerializer(serializers.ModelSerializer):
    class Meta:
        model = LensCleanerStock
        fields = ['id', 'lens_cleaner', 'initial_count', 'qty']       
        
class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = [
            'id',
            'order',
            'lens',
            'lens_cleaner',
            'frame',
            'quantity',
            'price_per_unit',
            'subtotal',
        ]

        def create(self, validated_data):
        # Calculate the subtotal based on quantity and price per unit
            validated_data['subtotal'] = validated_data['quantity'] * validated_data['price_per_unit']
            return super().create(validated_data)
        
class OrderPaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderPayment
        fields = [
            'id',
            'order',
            'payment_date',
            'amount',
            'payment_method',
            'transaction_status',
            'is_partial',
            'is_final_payment',
        ]

class OrderSerializer(serializers.ModelSerializer):
    order_items = OrderItemSerializer(many=True, read_only=True)
    order_payments = OrderPaymentSerializer(many=True, read_only=True, source='orderpayment_set')
    refraction = serializers.PrimaryKeyRelatedField(queryset=Refraction.objects.all(), allow_null=True)
    class Meta:
        model = Order
        fields = [
            'id',
            'customer',  # References the Refraction table
            'refraction', # ForeignKey to Refraction
            'order_date',
            'order_updated_date',
            'status',
            'sub_total',
            'discount',
            'total_price',
            'order_items',
            'order_payments'
        ] 
class DoctorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Doctor
        fields = ['id', 'name', 'contact_info', 'status']

class PatientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = ['id', 'name', 'date_of_birth', 'phone_number','address']

class ScheduleSerializer(serializers.ModelSerializer):
    doctor_name = serializers.CharField(source='doctor.name', read_only=True)  # Include doctor name if needed

    class Meta:
        model = Schedule
        fields = [
            'id',
            'doctor',  # Doctor ID
            'doctor_name',  # Doctor Name (Optional, based on `doctor.name`)
            'date',  # Schedule Date
            'start_time',  # Start Time
            'status',  # Schedule Status (e.g., Available, Booked, Unavailable)
            'created_at',  # Auto-generated creation timestamp
            'updated_at',  # Auto-generated update timestamp
        ]

class AppointmentSerializer(serializers.ModelSerializer):
    doctor_name = serializers.CharField(source='doctor.name', read_only=True)  # Doctor's name
    patient_name = serializers.CharField(source='patient.name', read_only=True)  # Patient's name
    schedule_date = serializers.DateField(source='schedule.date', read_only=True)  # Schedule date
    schedule_start_time = serializers.TimeField(source='schedule.start_time', read_only=True)  # Schedule start time

    class Meta:
        model = Appointment
        fields = [
            'id',
            'doctor',  # Doctor ID
            'doctor_name',  # Doctor's name
            'patient',  # Patient ID
            'patient_name',  # Patient's name
            'schedule',  # Schedule ID
            'schedule_date',  # Schedule date (from Schedule table)
            'schedule_start_time',  # Schedule start time (from Schedule table)
            'date',  # Appointment date
            'time',  # Appointment time
            'status',  # Appointment status (Pending, Confirmed, Completed, Cancelled)
            'amount',  # Channeling fee
            'channel_no',
            'created_at',  # Record creation timestamp
            'updated_at',  # Record update timestamp
        ]

class ChannelPaymentSerializer(serializers.ModelSerializer):
    appointment_details = serializers.CharField(source='appointment.id', read_only=True)  # Appointment ID
    doctor_name = serializers.CharField(source='appointment.doctor.name', read_only=True)  # Doctor's name
    patient_name = serializers.CharField(source='appointment.patient.name', read_only=True)  # Patient's name

    class Meta:
        model = ChannelPayment
        fields = [
            'id',
            'appointment',  # Appointment ID
            'appointment_details',  # Read-only appointment reference
            'doctor_name',  # Doctor's name (read-only)
            'patient_name',  # Patient's name (read-only)
            'payment_date',  # Date and time of payment
            'amount',  # Payment amount
            'payment_method',  # Payment method (cash or card)
            'is_final',  # Whether this is the final payment
            'created_at',  # Auto-generated timestamp for record creation
            'updated_at',  # Auto-generated timestamp for record updates
        ]
class ChannelListSerializer(serializers.ModelSerializer):
    doctor_name = serializers.CharField(source='doctor.name', read_only=True)
    patient_name = serializers.CharField(source='patient.name', read_only=True)
    address = serializers.CharField(source='patient.address', read_only=True)
    contact_number = serializers.CharField(source='patient.phone_number', read_only=True)
    first_payment = serializers.SerializerMethodField()

    class Meta:
        model = Appointment
        fields = [
            'id',  # Appointment ID (Channel ID)
            'address',
            'doctor_name',
            'contact_number',
            'patient_name',
            'channel_no',
            'first_payment',
            'date',  # For filtering
        ]

    def get_first_payment(self, obj):
        first_payment = obj.payments.first()  # Assuming related_name='payments' for ChannelPayment
        return first_payment.amount if first_payment else None
class AppointmentDetailSerializer(serializers.ModelSerializer):
    payments = serializers.SerializerMethodField()  # Custom field for payments
    doctor_name = serializers.CharField(source='doctor.name', read_only=True)
    patient_name = serializers.CharField(source='patient.name', read_only=True)
    address = serializers.CharField(source='patient.address', read_only=True)
    contact_number = serializers.CharField(source='patient.phone_number', read_only=True)

    class Meta:
        model = Appointment
        fields = [
            'id', 'doctor', 'doctor_name', 'patient', 'patient_name',
            'address', 'contact_number', 'schedule', 'date', 'time',
            'status', 'amount', 'channel_no', 'payments'
        ]

class ChannelPaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChannelPayment
        fields = ['id', 'amount', 'payment_method', 'is_final', 'created_at']


