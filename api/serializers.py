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
    ChannelPayment,
    CustomUser,
    Invoice,
    ExternalLens,
    ExternalLensPower,
    OtherItem,
    OtherItemStock,
    UserBranch
)

class BranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = '__all__'
        
class RefractionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Refraction
        fields = ['id', 'customer_full_name', 'customer_mobile', 'refraction_number', 'nic']
        read_only_fields = ['refraction_number']  # Auto-generated

class RefractionDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = RefractionDetails
        fields = [
            'id', 
            'refraction',  # ForeignKey to Refraction
            'patient',  # ForeignKey to patient
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
            'remark',
            'note',
            'is_manual',
            'pd',
            'h',
            'shuger'
        ]
  
class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ['id', 'name', 'brand_type'] 

class ColorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Color
        fields = ['id', 'name']
        
class CodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Code
        fields = ['id', 'name', 'brand']
        
class FrameSerializer(serializers.ModelSerializer):
    brand_name = serializers.CharField(source='brand.name', read_only=True)  # ✅ Get brand name
    code_name = serializers.CharField(source='code.name', read_only=True)    # ✅ Get code name
    color_name = serializers.CharField(source='color.name', read_only=True)  # ✅ Get color name

    class Meta:
        model = Frame
        fields = [
            'id',
            'brand', 'brand_name',  
            'code', 'code_name',   
            'color', 'color_name',  
            'price',
            'size',
            'species',
            'image',
        ]
        
class FrameStockSerializer(serializers.ModelSerializer):
    branch_id = serializers.PrimaryKeyRelatedField(
        queryset=Branch.objects.all(),  # Ensures valid branch selection
        source="branch",  # Maps to `branch` field in the model
        required=False  # Makes it optional in requests
    )
    branch_name = serializers.CharField(source="branch.branch_name", read_only=True) 
    class Meta:
        model = FrameStock
        fields = ['id', 'frame', 'qty', 'initial_count','limit','branch_id','branch_name']
        
class LenseTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LenseType
        fields = ['id', 'name', 'description']       
class ExternalLensTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LenseType
        fields = ['id', 'name', 'description']
        
class CoatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coating
        fields = ['id', 'name', 'description']
        
class LensSerializer(serializers.ModelSerializer):
    brand = serializers.PrimaryKeyRelatedField(queryset=Brand.objects.all())
    brand_name = serializers.CharField(source='brand.name', read_only=True)  # ✅ Get brand name  
    type_name = serializers.CharField(source='type.name', read_only=True)  # ✅ Get brand name 
    coating_name = serializers.CharField(source='coating.name', read_only=True)  # ✅ Get brand name 
    class Meta:
        model = Lens
        fields = ['id', 'type', 'coating', 'price','brand', 'brand_name','type_name','coating_name']

    def validate(self, data):
        if 'brand' not in data:
            raise serializers.ValidationError("Brand is required.")
        return data       
class LensStockSerializer(serializers.ModelSerializer):
    lens_type = serializers.CharField(source='lens.type.name', read_only=True)  # Assuming Lens has a type field
    coating = serializers.CharField(source='lens.coating.name', read_only=True)  # Assuming Lens has a coating field
    powers = serializers.SerializerMethodField()
    class Meta:
        model = LensStock
        fields = ['id', 'lens', 'lens_type','coating', 'initial_count', 'qty', 'limit', 'powers', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

    def get_powers(self, obj):
        """Fetch related powers for the lens."""
        powers = LensPower.objects.filter(lens=obj.lens)  # Assuming LensPower is related to Lens
        return LensPowerSerializer(powers, many=True).data
        
class PowerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Power
        fields = ['id', 'name']
        
class LensPowerSerializer(serializers.ModelSerializer):
    side = serializers.ChoiceField(
        choices=[('left', 'Left'), ('right', 'Right')],
        allow_null=True,  # ✅ Allows NULL values in the API
        required=False  # ✅ Makes the field optional in requests
    )
    class Meta:
        model = LensPower
        fields = ['id', 'lens', 'power', 'value', 'side']

class ExternalLensPowerSerializer(serializers.ModelSerializer):
    side = serializers.ChoiceField(
        choices=[('left', 'Left'), ('right', 'Right')],
        allow_null=True,
        required=False
    )
    power_name = serializers.CharField(source='power.name', read_only=True)

    class Meta:
        model = ExternalLensPower
        fields = ['id', 'external_lens', 'power', 'value', 'side', 'power_name']

class LensCleanerStockSerializer(serializers.ModelSerializer):
    class Meta:
        model = LensCleanerStock
        fields = ['id', 'initial_count', 'qty'] 
        
class LensCleanerSerializer(serializers.ModelSerializer):
    """
    Serializer for LensCleaner with Stock.
    """
    stocks = LensCleanerStockSerializer(many=True, required=False)  # ✅ Stock can be updated without IDs

    class Meta:
        model = LensCleaner
        fields = ['id', 'name', 'price', 'stocks','is_active']

    def update(self, instance, validated_data):
        """
        Override update to handle stock updates without requiring an ID.
        """
        stocks_data = validated_data.pop('stocks', [])  # ✅ Extract stock data
        instance.name = validated_data.get('name', instance.name)
        instance.price = validated_data.get('price', instance.price)
        instance.save()

        # ✅ Check if stock exists for this lens cleaner
        existing_stock = instance.stocks.first()  # Since there's only **one stock entry per cleaner**

        if stocks_data:
            stock_data = stocks_data[0]  # We only expect **one stock entry**
            if existing_stock:
                # ✅ Update existing stock
                existing_stock.initial_count = stock_data.get('initial_count', existing_stock.initial_count)
                existing_stock.qty = stock_data.get('qty', existing_stock.qty)
                existing_stock.save()
            else:
                # ✅ Create new stock entry (no existing stock)
                LensCleanerStock.objects.create(lens_cleaner=instance, **stock_data)

        # ✅ REFRESH `instance` TO LOAD UPDATED STOCK VALUES
        instance.refresh_from_db()  # 🔥 This ensures we return the updated stock in the response

        return instance
        
class OrderItemSerializer(serializers.ModelSerializer):
    lens_name = serializers.CharField(source="lens.type.name", read_only=True)  # ✅ Get lens type name
    type_name = serializers.CharField(source="external_lens.type.name", read_only=True)  # ✅ Get lens type name
    type_id = serializers.CharField(source="external_lens.type.id", read_only=True)  # ✅ Get lens type name
    coating_name = serializers.CharField(source="external_lens.coating.name", read_only=True)  # ✅ Get lens coating name
    coating_id = serializers.IntegerField(source="external_lens.coating.id", read_only=True)
    brand_name = serializers.CharField(source="external_lens.brand.name", read_only=True)  # ✅ Get lens brand name
    brand_id = serializers.CharField(source="external_lens.brand.id", read_only=True)  # ✅ Get lens brand name
    frame_name = serializers.CharField(source="frame.code", read_only=True)  # ✅ Get frame name
    lens_cleaner_name = serializers.CharField(source="lens_cleaner.name", read_only=True)  # ✅ Get cleaner name
    lens_powers = serializers.SerializerMethodField()  # ✅ Custom field for lens powers
    external_lens_powers = serializers.SerializerMethodField()  # ✅ Custom field for external lens powers
    is_non_stock = serializers.BooleanField(default=False) 
    lens_detail = LensSerializer(source="lens", read_only=True)
    frame_detail = FrameSerializer(source="frame", read_only=True)
    class Meta:
        model = OrderItem
        fields = [
            'id',
            'order',
            'lens', 'lens_name',  # ✅ Return lens name
            'external_lens','type_name','type_id',
            'frame', 'frame_name',  # ✅ Return frame name
            'lens_cleaner', 'lens_cleaner_name',  # ✅ Return lens cleaner name
            'coating_name',
            'coating_id',
            'brand_name',
            'brand_id',
            'quantity',
            'price_per_unit',
            'subtotal',
            'lens_powers',  # ✅ Include lens powers
            'external_lens_powers',
            'is_non_stock' ,
            'lens_detail',
            'frame_detail'
        ]

    def get_lens_powers(self, obj):
        """ ✅ Fetch lens powers for the given lens. """
        if obj.lens:
            powers = obj.lens.lens_powers.all()
            return LensPowerSerializer(powers, many=True).data
        return []
    
    def get_external_lens_powers(self, obj):
        """ ✅ Fetch lens powers for the given external lens. """
        if obj.external_lens:
            powers = obj.external_lens.external_lens_powers.all()  
            return ExternalLensPowerSerializer(powers, many=True).data
        return []


    def create(self, validated_data):
        """ ✅ Auto-calculate subtotal before saving. """
        price = validated_data.get('price_per_unit', 0)  # ✅ Ensure price exists
        quantity = validated_data.get('quantity', 1)  # ✅ Default quantity to 1

        validated_data['subtotal'] = price * quantity
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
    refraction = serializers.PrimaryKeyRelatedField(queryset=Refraction.objects.all(), allow_null=True, required=False) 
    sales_staff_code = serializers.PrimaryKeyRelatedField(queryset=CustomUser.objects.all(), allow_null=True, required=False)
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
            'order_payments',
            'sales_staff_code',
            'remark'
        ] 

class ExternalLensSerializer(serializers.ModelSerializer):
    brand_name = serializers.CharField(source="brand.name", read_only=True)  # ✅ Fetch Brand Name
    type_name = serializers.CharField(source="type.name", read_only=True)  # ✅ Fetch Lens Type Name
    coating_name = serializers.CharField(source="coating.name", read_only=True)  # ✅ Fetch Coating Name

    class Meta:
        model = ExternalLens
        fields = [
            "id",
            "brand", "brand_name",  # ✅ Return ID & Name
            "type", "type_name",  # ✅ Return ID & Name
            "coating", "coating_name",  # ✅ Return ID & Name
            "price",  # ✅ Manually Entered Price
        ]

class PatientSerializer(serializers.ModelSerializer):
    refraction_number = serializers.SerializerMethodField()
    class Meta:
        model = Patient
        fields = ['id', 'name', 'date_of_birth', 'phone_number','address','nic','refraction_id','refraction_number']
    def get_refraction_number(self, obj):
        # Fetch the related Refraction instance using refraction_id
        refraction = Refraction.objects.filter(id=obj.refraction_id).first()
        return refraction.refraction_number if refraction else None
        

class InvoiceSerializer(serializers.ModelSerializer):
    customer = serializers.PrimaryKeyRelatedField(source='order.customer', read_only=True)  # ✅ Fetch customer ID
    customer_details = PatientSerializer(source='order.customer', read_only=True)  # ✅ Full customer details
    refraction_details = RefractionSerializer(source='order.refraction', read_only=True)  # ✅ Refraction details (if exists)
    order_details = OrderSerializer(source='order', read_only=True)  # ✅ Full order details

    class Meta:
        model = Invoice
        fields = [
            'id',
            'order',       # Order ID (ForeignKey)
            'customer',    # ✅ Customer ID (from Order)
            'customer_details',  # ✅ Full customer details
            'refraction_details',  # ✅ Full refraction details (if available)
            'invoice_type',  # "factory" or "manual"
            'daily_invoice_no',  # Unique daily number for factory invoices
            'invoice_date',
            'order_details',  # ✅ Full order details (optional)
        ]

class DoctorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Doctor
        fields = ['id', 'name', 'contact_info', 'status']
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
    def get_payments(self, obj):
        """Fetch all related payments for this appointment."""
        payments = ChannelPayment.objects.filter(appointment=obj)  # Related payments
        return ChannelPaymentSerializer(payments, many=True).data 
class OtherItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OtherItem
        fields = ['id', 'name', 'price', 'is_active']
class OtherItemStockSerializer(serializers.ModelSerializer):
    other_item = OtherItemSerializer(read_only=True)  # ✅ Nested serialization for better readability
    other_item_id = serializers.PrimaryKeyRelatedField(
        queryset=OtherItem.objects.all(), source='other_item', write_only=True
    )
    branch_id = serializers.PrimaryKeyRelatedField(
        queryset=Branch.objects.all(),  # Ensures valid branch selection
        source="branch",  # Maps to `branch` field in the model
        required=False  # Makes it optional in requests
    )
    branch_name = serializers.CharField(source="branch.branch_name", read_only=True) 

    class Meta:
        model = OtherItemStock
        fields = ['id', 'other_item', 'other_item_id', 'initial_count', 'qty', 'branch_name','branch_id']	

class UserBranchSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(queryset=CustomUser.objects.all())  # Accepts user ID
    branch = serializers.PrimaryKeyRelatedField(queryset=Branch.objects.all())  # Accepts branch ID
    user_username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = UserBranch
        fields = ['id', 'user', 'branch', 'assigned_at',"user_username",]
        read_only_fields = ['assigned_at']



