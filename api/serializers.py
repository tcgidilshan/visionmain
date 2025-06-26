from rest_framework import serializers
from django.db.models import Sum
from django.db import models
from rest_framework.exceptions import ValidationError
import os
from .models import (
    Branch,Refraction,RefractionDetails,RefractionDetailsAuditLog,
    Brand,Color,Code,Frame,
    FrameStock,
    LenseType,
    Coating,
    Lens,
    LensStock,
    Power,
    LensPower,LensCleaner,
    LensCleanerStock,Order,OrderItem,OrderPayment,Doctor,Patient,Schedule,Appointment,
    ChannelPayment,SolderingOrder, SolderingInvoice, SolderingPayment,
    CustomUser,SafeTransaction,SafeBalance,
    Invoice,ExternalLensCoating, ExternalLensBrand,
    ExternalLens,BusSystemSetting,
    OtherItem,BankAccount,BankDeposit,
    OtherItemStock,Expense,OtherIncome,OtherIncomeCategory,
    UserBranch,ExpenseMainCategory, ExpenseSubCategory,
    DoctorClaimInvoice,DoctorClaimChannel,MntOrder,OrderProgress,OrderAuditLog,OrderItemWhatsAppLog,ArrivalStatus
)

class BranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = '__all__'


class BankAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankAccount
        fields = ['id', 'account_number', 'bank_name', 'branch']
        
class RefractionSerializer(serializers.ModelSerializer):
    branch_id = serializers.PrimaryKeyRelatedField(
        queryset=Branch.objects.all(), source='branch', required=False
    )
    branch_name = serializers.CharField(source='branch.branch_name', read_only=True)
    class Meta:
        model = Refraction
        fields = ['id', 'customer_full_name', 'customer_mobile', 'refraction_number', 'nic', 'branch_id', 'branch_name','created_at']
        read_only_fields = ['refraction_number']  # Auto-generated

class RefractionDetailsSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(queryset=CustomUser.objects.all())  # Accepts user ID
    username = serializers.CharField(
        source='user.username', 
        read_only=True  # Only for output
    )
    prescription_type_display = serializers.CharField(
        source='get_prescription_type_display', read_only=True
    )
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
            'refraction_remark',
            'note',
            'is_manual',
            'shuger',
            'cataract',
            'user',
            'prescription_type',        
            'prescription_type_display',  
            'username', 
            'blepharitis'
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
    brand_name = serializers.CharField(source='brand.name', read_only=True)
    class Meta:
        model = Code
        fields = ['id', 'name', 'brand','brand_name']
        
class FrameSerializer(serializers.ModelSerializer):
    brand_name = serializers.CharField(source='brand.name', read_only=True)  # Get brand name
    code_name = serializers.CharField(source='code.name', read_only=True)    # Get code name
    color_name = serializers.CharField(source='color.name', read_only=True)  # Get color name
    brand_type_display = serializers.CharField(source='get_brand_type_display', read_only=True)
    image_url = serializers.SerializerMethodField()
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
            'brand_type',
            'brand_type_display',
            'is_active',
            'image_url',

        ]
    def validate_image(self, value):
    # Accept only supported types
        if value and not value.name.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
            raise serializers.ValidationError("Only PNG, JPG, JPEG, or WEBP files are allowed.")
        return value
    def get_image_url(self, obj):
        if not obj.image:
            return None
            
        # Get the URL and remove any leading slashes to prevent double /media/
        relative_url = obj.image.url.lstrip('/')
        request = self.context.get('request')
        
        if request is not None:
            return request.build_absolute_uri(f'/{relative_url}')
        
        # Try Django sites framework
        try:
            from django.contrib.sites.shortcuts import get_current_site
            from django.conf import settings
            
            site = get_current_site(None)
            scheme = 'https' if getattr(settings, 'SECURE_SSL_REDIRECT', False) else 'http'
            base_url = f"{scheme}://{site.domain}"
            return f"{base_url}/{relative_url}"
            
        except Exception as e:
            # Fallback to environment variable or default
            from dotenv import load_dotenv
            import os
            
            # Load environment variables from .env file
            load_dotenv()
            
            # Get SITE_URL from environment variables or use default
            base_url = os.getenv('SITE_URL', 'http://127.0.0.1:8000')
            return f"{base_url.rstrip('/')}/{relative_url}"
            
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
    brand_name = serializers.CharField(source='brand.name', read_only=True)  # Get brand name  
    type_name = serializers.CharField(source='type.name', read_only=True)  # Get brand name 
    coating_name = serializers.CharField(source='coating.name', read_only=True)  # Get brand name 

    class Meta:
        model = Lens
        fields = ['id', 'type', 'coating', 'price','brand','branch', 'brand_name','type_name','coating_name','is_active']

    def validate(self, data):
        if 'brand' not in data:
            raise serializers.ValidationError("Brand is required.")
        return data       
class LensStockSerializer(serializers.ModelSerializer):
    lens_type = serializers.CharField(source='lens.type.name', read_only=True)  # Assuming Lens has a type field
    coating = serializers.CharField(source='lens.coating.name', read_only=True)  # Assuming Lens has a coating field
    powers = serializers.SerializerMethodField()
    branch_id = serializers.PrimaryKeyRelatedField(
        queryset=Branch.objects.all(),  # Ensures valid branch selection
        source="branch",  # Maps to `branch` field in the model
        required=False  # Makes it optional in requests
    )
    branch_name = serializers.CharField(source="branch.branch_name", read_only=True) 
    class Meta:
        model = LensStock
        fields = ['id', 'lens','branch_id','branch_name', 'lens_type','coating', 'initial_count', 'qty', 'limit', 'powers', 'created_at', 'updated_at']
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
        allow_null=True,  #  Allows NULL values in the API
        required=False  #  Makes the field optional in requests
    )
    power_name=serializers.CharField(source='power.name', read_only=True)
    class Meta:
        model = LensPower
        fields = ['id', 'lens', 'power', 'value', 'side','power_name']

class LensCleanerStockSerializer(serializers.ModelSerializer):
    branch_id = serializers.PrimaryKeyRelatedField(
        queryset=Branch.objects.all(), source="branch", required=False
    )
    branch_name = serializers.CharField(source="branch.branch_name", read_only=True)
    class Meta:
        model = LensCleanerStock
        fields = ['id', 'initial_count', 'qty', 'initial_count', 'branch_id', 'branch_name']
        
class LensCleanerSerializer(serializers.ModelSerializer):
    """
    Serializer for LensCleaner with Stock.
    """
    stocks = LensCleanerStockSerializer(many=True, required=False)  #  Stock can be updated without IDs

    class Meta:
        model = LensCleaner
        fields = ['id', 'name', 'price', 'stocks','is_active']

    def update(self, instance, validated_data):
        """
        Override update to handle stock updates without requiring an ID.
        """
        stocks_data = validated_data.pop('stocks', [])  #  Extract stock data
        instance.name = validated_data.get('name', instance.name)
        instance.price = validated_data.get('price', instance.price)
        instance.save()

        #  Check if stock exists for this lens cleaner
        existing_stock = instance.stocks.first()  # Since there's only **one stock entry per cleaner**

        if stocks_data:
            stock_data = stocks_data[0]  # We only expect **one stock entry**
            if existing_stock:
                #  Update existing stock
                existing_stock.initial_count = stock_data.get('initial_count', existing_stock.initial_count)
                existing_stock.qty = stock_data.get('qty', existing_stock.qty)
                existing_stock.save()
            else:
                #  Create new stock entry (no existing stock)
                LensCleanerStock.objects.create(lens_cleaner=instance, **stock_data)

        #  REFRESH `instance` TO LOAD UPDATED STOCK VALUES
        instance.refresh_from_db()  #  This ensures we return the updated stock in the response

        return instance
    
class OtherItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OtherItem
        fields = ['id', 'name', 'price', 'is_active']
        
class OrderItemSerializer(serializers.ModelSerializer):
    # External Lens Info
    type_id        = serializers.IntegerField(source="external_lens.lens_type.id", read_only=True)
    type_name      = serializers.CharField(source="external_lens.lens_type.name", read_only=True)
    coating_id     = serializers.IntegerField(source="external_lens.coating.id", read_only=True)
    coating_name   = serializers.CharField(source="external_lens.coating.name", read_only=True)
    brand_id       = serializers.IntegerField(source="external_lens.brand.id", read_only=True)
    brand_name     = serializers.CharField(source="external_lens.brand.name", read_only=True)
    ex_branded_type= serializers.CharField(source="external_lens.branded", read_only=True)

    # Detail serializers (readonly)
    lens_detail        = LensSerializer(source="lens", read_only=True)
    frame_detail       = FrameSerializer(source="frame", read_only=True)
    other_item_detail  = OtherItemSerializer(source="other_item", read_only=True)

    # Other fields
    lens_powers   = serializers.SerializerMethodField()  # Optional/custom field
    is_non_stock  = serializers.BooleanField(default=False)
    external_lens = serializers.PrimaryKeyRelatedField(queryset=ExternalLens.objects.all(), required=False)
    
    note = serializers.CharField(allow_blank=True, allow_null=True, required=False)
    user_username = serializers.CharField(source='user.username', read_only=True)
    admin_username = serializers.CharField(source='admin.username', read_only=True)
    deleted_at = serializers.DateTimeField(read_only=True)
    class Meta:
        model = OrderItem
        fields = [
            'id',
            'order',
            'lens',
            'type_id',
            'type_name',
            'frame',
            'lens_cleaner',
            'external_lens',
            'other_item',
            'coating_id',
            'coating_name',
            'brand_id',
            'brand_name',
            'quantity',
            'price_per_unit',
            'subtotal',
            'lens_powers',
            'is_non_stock',
            'lens_detail',
            'frame_detail',
            'other_item_detail',
            'note',
            'user_username',
            'admin_username',
            'user',
            'admin',
            'deleted_at',
            'ex_branded_type'
        ]


    def get_lens_powers(self, obj):
        """  Fetch lens powers for the given lens. """
        if obj.lens:
            powers = obj.lens.lens_powers.all()
            return LensPowerSerializer(powers, many=True).data
        return []

    def create(self, validated_data):
        """  Auto-calculate subtotal before saving. """
        price = validated_data.get('price_per_unit', 0)  #  Ensure price exists
        quantity = validated_data.get('quantity', 1)  #  Default quantity to 1

        validated_data['subtotal'] = price * quantity
        return super().create(validated_data)

class OrderPaymentSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    admin_username = serializers.CharField(source='admin.username', read_only=True)
    deleted_at = serializers.DateTimeField(read_only=True)
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
            'user',
            'admin',
            'user_username',
            'admin_username',
            'deleted_at'
        ]

class OrderSerializer(serializers.ModelSerializer):
    order_items = OrderItemSerializer(many=True, read_only=True)
    order_payments = serializers.SerializerMethodField()
    refraction = serializers.PrimaryKeyRelatedField(queryset=Refraction.objects.all(), allow_null=True, required=False) 
    sales_staff_code = serializers.PrimaryKeyRelatedField(queryset=CustomUser.objects.all(), allow_null=True, required=False)
    branch_id = serializers.PrimaryKeyRelatedField(
        queryset=Branch.objects.all(), source='branch', required=False
    )
    sales_staff_username = serializers.CharField(
        source='sales_staff_code.username', 
        read_only=True
    )
    branch_name = serializers.CharField(source='branch.branch_name', read_only=True)
    invoice_number = serializers.PrimaryKeyRelatedField(source='invoice.invoice_number', read_only=True)
    user_date = serializers.DateField(required=False)
    bus_title = serializers.PrimaryKeyRelatedField(
        queryset=BusSystemSetting.objects.all(), required=False, allow_null=True
    )
    bus_title_name = serializers.PrimaryKeyRelatedField(source='bus_title.title', read_only=True)
    issued_by = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.all(), allow_null=True, required=False
    )
    is_refund = serializers.BooleanField(read_only=True)
    deleted_at = serializers.DateTimeField(read_only=True)
    refunded_at = serializers.DateTimeField(read_only=True)
    issued_by_user_name = serializers.CharField(source='issued_by.username', read_only=True)
    issued_by_user_code = serializers.CharField(source='issued_by.user_code', read_only=True)
    issued_date = serializers.DateTimeField(read_only=True)
    progress_status = serializers.SerializerMethodField()
    mnt_order = serializers.SerializerMethodField()
    
    def get_mnt_order(self, obj):
        mnt_order = obj.mnt_orders.first()  # Get the first MNT order if exists
        if mnt_order:
            return {
                'id': mnt_order.id,
                'mnt_number': mnt_order.mnt_number,
                'created_at': mnt_order.created_at,
                'user_username': mnt_order.user.username if mnt_order.user else None,
                'admin_username': mnt_order.admin.username if mnt_order.admin else None
            }
        return None
    
    def to_representation(self, instance):
        if instance.is_deleted:
            raise serializers.ValidationError("This order has been deleted.")
        return super().to_representation(instance)
    
    def get_order_items(self, obj):
        items = obj.order_items.filter(is_deleted=False)
        return OrderItemSerializer(items, many=True).data
    
    def get_order_payments(self, obj):
        payments = obj.orderpayment_set.filter(is_deleted=False)
        return OrderPaymentSerializer(payments, many=True).data
    def get_progress_status(self, obj):
        last_status = obj.order_progress_status.order_by('-changed_at').first()
        if last_status:
            return OrderProgressSerializer(last_status).data
        return None

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
            'branch_id', 
            'branch_name',
            'order_remark',
            'pd',
            'height',
            'right_height',
            'left_height',
            'left_pd',
            'right_pd',
            'fitting_on_collection',
            'on_hold',
            'sales_staff_username',
            'invoice_number',
            'user_date',
            'bus_title',
            'bus_title_name',
            'issued_by',
            'issued_by_user_name',
            'issued_by_user_code',
            'issued_date',
            'progress_status',
            'fitting_status',
            'fitting_status_updated_date',
            'is_refund',
            'deleted_at',
            'refunded_at',
            'urgent',
            'mnt_order'
        ] 
class OrderAuditLogSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)
    admin_name = serializers.CharField(source='admin.username', read_only=True)
    
    class Meta:
        model = OrderAuditLog
        fields = [
            'id',
            'order',
            'field_name',
            'old_value',
            'user',
            'admin', 
            'created_at',  
            'user_name' ,
            'admin_name',
        ]

class BulkWhatsAppLogCreateSerializer(serializers.Serializer):
    order_ids = serializers.ListField(child=serializers.IntegerField(), allow_empty=False)
    urgent_order_ids = serializers.ListField(child=serializers.IntegerField(), required=False, default=list)

    def validate(self, data):
        order_ids = set(data['order_ids'])
        urgent_order_ids = set(data.get('urgent_order_ids', []))
        if not urgent_order_ids.issubset(order_ids):
            raise serializers.ValidationError("urgent_order_ids must be a subset of order_ids.")
        return data

class ArrivalStatusBulkCreateSerializer(serializers.Serializer):
    order_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=False
    )

    def validate_order_ids(self, value):
        if len(set(value)) != len(value):
            raise serializers.ValidationError("Duplicate order_ids detected.")
        return value

class ExternalLensSerializer(serializers.ModelSerializer):
    lens_type_name     = serializers.CharField(source='lens_type.name', read_only=True)
    coating_name       = serializers.CharField(source='coating.name', read_only=True)
    brand_name         = serializers.CharField(source='brand.name', read_only=True)
    branded_display    = serializers.CharField(source='get_branded_display', read_only=True)

    class Meta:
        model = ExternalLens
        fields = [
            'id',
            'branch',
            'lens_type',
            'lens_type_name',
            'coating',
            'coating_name',
            'brand',
            'brand_name',
            'branded',
            'branded_display',
            'price',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def validate(self, data):
        # On create only
        if self.instance is None:
            exists = ExternalLens.objects.filter(
                lens_type=data.get('lens_type'),
                coating=data.get('coating'),
                brand=data.get('brand'),
                branded=data.get('branded')
            ).exists()

            if exists:
                raise ValidationError({
                    'lens_type': "This lens type already exists with the selected coating, brand, and branded value."
                })
        return data
    
class ExternalLensCoatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExternalLensCoating
        fields = ['id', 'name', 'description']

class ExternalLensBrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExternalLensBrand
        fields = ['id', 'name']

class PatientSerializer(serializers.ModelSerializer):
    refraction_number = serializers.SerializerMethodField()
    class Meta:
        model = Patient
        fields = ['id', 'name', 'date_of_birth', 'phone_number','address','nic','patient_note','refraction_id','refraction_number']
    def get_refraction_number(self, obj):
        # Fetch the related Refraction instance using refraction_id
        refraction = Refraction.objects.filter(id=obj.refraction_id).first()
        return refraction.refraction_number if refraction else None
        

class InvoiceSerializer(serializers.ModelSerializer):
    customer = serializers.PrimaryKeyRelatedField(source='order.customer', read_only=True)  #  Fetch customer ID
    customer_details = PatientSerializer(source='order.customer', read_only=True)  #  Full customer details
    order_details = OrderSerializer(source='order', read_only=True)  #  Full order details
    refraction_details = serializers.SerializerMethodField()
    
    class Meta:
        model = Invoice
        fields = [
            'id',
            'order',       # Order ID (ForeignKey)
            'customer',    #  Customer ID (from Order)
            'customer_details',  #  Full customer details
            'refraction_details',  #  Full refraction details (if available)
            'invoice_type',  # "factory" or "manual"
            'daily_invoice_no',  # Unique daily number for factory invoices
            'invoice_number',
            'invoice_date',
            'order_details',  #  Full order details (optional)
              #  NEW fields for tracking factory invoice progress
        ]

    def get_refraction_details(self, obj):
        refraction = getattr(obj.order, 'refraction', None)
        if refraction:
            # This assumes RefractionDetails has a ForeignKey to Refraction
            from api.models import RefractionDetails  # adjust path as needed
            try:
                details = RefractionDetails.objects.get(refraction=refraction)
                return RefractionDetailsSerializer(details).data
            except RefractionDetails.DoesNotExist:
                return None
        return None

class DoctorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Doctor
        fields = ['id', 'name', 'contact_info', 'status', 'specialization']
        
class ScheduleSerializer(serializers.ModelSerializer):
    doctor_name = serializers.CharField(source='doctor.name', read_only=True)  # Include doctor name if needed
    branch_name = serializers.CharField(source='branch.branch_name', read_only=True)

    class Meta:
        model = Schedule
        fields = [
            'id',
            'doctor',  # Doctor ID
            'doctor_name',  # Doctor Name (Optional, based on `doctor.name`)
            'branch',        # branch ID
            'branch_name', 
            'date',  # Schedule Date
            'start_time',  # Start Time
            'status',  # Schedule Status (e.g., Available, Booked, Unavailable)
            'created_at',  # Auto-generated creation timestamp
            'updated_at',  # Auto-generated update timestamp
        ]

class AppointmentSerializer(serializers.ModelSerializer):
    doctor_name = serializers.CharField(source='doctor.name', read_only=True)  # Doctor's name
    patient_name = serializers.CharField(source='patient.name', read_only=True)  # Patient's name
    branch_name = serializers.CharField(source='branch.branch_name', read_only=True)  # Patient's name
    schedule_date = serializers.DateField(source='schedule.date', read_only=True)  # Schedule date
    schedule_start_time = serializers.TimeField(source='schedule.start_time', read_only=True)  # Schedule start time
    invoice_number = serializers.IntegerField(read_only=True)
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
            'branch',
            'updated_at',  # Record update timestamp
            'branch_name',
            'invoice_number',
            'note'
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
    invoice_number = serializers.IntegerField(read_only=True)
    total_payment = serializers.SerializerMethodField(read_only=True)
    balance = serializers.SerializerMethodField()
    is_deleted = serializers.BooleanField(read_only=True)
    is_refund = serializers.BooleanField(read_only=True)
    deleted_at = serializers.DateTimeField(read_only=True)
    refunded_at = serializers.DateTimeField(read_only=True)

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
            'invoice_number',
            'date',  # For filtering
            'time',
            'total_payment',
            'balance',
            'amount',
            'note',
            'is_deleted',
            'is_refund',
            'deleted_at',
            'refunded_at'
        ]

    def get_first_payment(self, obj):
        first_payment = obj.payments.first()  # Assuming related_name='payments' for ChannelPayment
        return first_payment.amount if first_payment else None
    
    def get_total_payment(self, obj):
        return obj.payments.aggregate(total=Sum('amount'))['total'] or 0
    
    def get_balance(self, obj):
        total_paid = self.get_total_payment(obj)
        total_fee = obj.amount or 0  # or obj.amount, depending on your field naming
        return total_fee - total_paid

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
            'status', 'amount', 'channel_no', 'payments','invoice_number','note',
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
    other_item_id = serializers.PrimaryKeyRelatedField(
        queryset=OtherItem.objects.all(), source='other_item', write_only=True
    )
    branch_id = serializers.PrimaryKeyRelatedField(
        queryset=Branch.objects.all(),  # Ensures valid branch selection
        source="branch",  # Maps to `branch` field in the model
        required=False  # Makes it optional in requests
    )
    class Meta:
        model = OtherItemStock
        fields = ['id', 'other_item_id', 'initial_count', 'qty','branch_id','limit']	

class UserBranchSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(queryset=CustomUser.objects.all())  # Accepts user ID
    branch = serializers.PrimaryKeyRelatedField(queryset=Branch.objects.all())  # Accepts branch ID
    user_username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = UserBranch
        fields = ['id', 'user', 'branch', 'assigned_at',"user_username",]
        read_only_fields = ['assigned_at']

class OrderProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderProgress
        fields = ['id', 'progress_status', 'changed_at']

class InvoiceSearchSerializer(serializers.ModelSerializer):
    customer = serializers.PrimaryKeyRelatedField(source='order.customer.name', read_only=True)  # Fetch customer ID
    # customer_details = PatientSerializer(source='order.customer', read_only=True)  #  Full customer details
    # refraction_details = RefractionSerializer(source='order.refraction', read_only=True)  # Refraction details (if exists)
    payments = serializers.SerializerMethodField()
    total_price = serializers.DecimalField(
    source='order.total_price',
    max_digits=10,  # Use the same as your model
    decimal_places=2,  # Use the same as your model
    read_only=True
)
    fitting_on_collection = serializers.BooleanField(
        source='order.fitting_on_collection', read_only=True
    )
    on_hold = serializers.BooleanField(
        source='order.on_hold', read_only=True
    )
    urgent = serializers.BooleanField(
        source='order.urgent', read_only=True
    )
    #TODO: Access issued_by via the related Order object.
    issued_by_user_name = serializers.CharField(
        source='order.issued_by.username', read_only=True
    )
    issued_by_user_code = serializers.CharField(
        source='order.issued_by.user_code', read_only=True
    )
    issued_by = serializers.PrimaryKeyRelatedField(
        source='order.issued_by', read_only=True
    )
    issued_date = serializers.DateTimeField(
        source='order.issued_date', read_only=True
    )
    fitting_status_updated_date = serializers.DateTimeField(
        source='order.fitting_status_updated_date', read_only=True
    )
    fitting_status = serializers.CharField(
        source='order.fitting_status', read_only=True
    )
    progress_status = serializers.SerializerMethodField()
    whatsapp_sent = serializers.SerializerMethodField()
    arrival_status = serializers.SerializerMethodField()
    #get mni invoice number 
    mnt_number = serializers.SerializerMethodField()
    
    
    
    class Meta:
        model = Invoice
        fields = [
            'id',
            'order',       # Order ID (ForeignKey)
            'customer',   
            'invoice_type',  # "factory" or "manual"
            'daily_invoice_no',  # Unique daily number for factory invoices
            'invoice_number',
            'invoice_date',
            'total_price',
            'whatsapp_sent',
            'arrival_status',
            'fitting_on_collection',
            'on_hold',
            'payments',
            'issued_by',
            'issued_by_user_name',
            'issued_by_user_code',
            'issued_date',
            'progress_status',
            'urgent',
            'fitting_status',
            'fitting_status_updated_date',
            'mnt_number'
        ]
  
    def get_mnt_number(self, obj):
        mnt_order = obj.order.mnt_orders.first()  # Get the first MNT order if exists
        if mnt_order:
            return mnt_order.mnt_number
        return None
    def get_progress_status(self, obj):
        order = getattr(obj, "order", None)
        if not order:
            return None  # return None if order not present

        # Get the latest (last) progress status by changed_at DESCENDING
        last_status = order.order_progress_status.order_by('-changed_at').first()
        if last_status:
            return OrderProgressSerializer(last_status).data
        return None  # return None if there is no status


    def get_payments(self, obj):
            # Get the order related to this invoice
            order = obj.order
            if order:
                # Get all payments related to this order
                payments = order.orderpayment_set.all()
                # Serialize them
                from .serializers import OrderPaymentSerializer  # Avoid circular import if needed
                return OrderPaymentSerializer(payments, many=True).data
            return []
    def get_whatsapp_sent(self, obj):
        # Get the order related to this order item
        order = getattr(obj, "order", None)
        if not order:
            return None
                
        # Get the latest WhatsApp status log
        last_whatsapp_log = order.whatsapp_logs.order_by('-created_at').first()
        if last_whatsapp_log:
            return WhatsAppLogSerializer(last_whatsapp_log).data
        return None
    def get_arrival_status(self, obj):
        order = getattr(obj, "order", None)
        if not order:
            return None
        
        # Get the latest arrival status for this order
        last_arrival_status = ArrivalStatus.objects.filter(
            order=order,                      
        ).order_by('-created_at').first()
        
        if last_arrival_status:
            return ArrivalStatusSerializer(last_arrival_status).data
        return None
class ExpenseMainCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseMainCategory
        fields = ['id', 'name']


class ExpenseSubCategorySerializer(serializers.ModelSerializer):
    main_category_name = serializers.CharField(source='main_category.name', read_only=True)

    class Meta:
        model = ExpenseSubCategory
        fields = ['id', 'main_category', 'main_category_name', 'name']

# serializers.py
class ExpenseSerializer(serializers.ModelSerializer):
    main_category_name = serializers.CharField(source='main_category.name', read_only=True)
    sub_category_name = serializers.CharField(source='sub_category.name', read_only=True)
    class Meta:
        model = Expense
        fields = ['id', 'branch', 'main_category', 'sub_category', 'amount', 'note','paid_source', 'paid_from_safe', 'created_at','main_category_name','sub_category_name']

class ExpenseReportSerializer(serializers.ModelSerializer):
    main_category_name = serializers.CharField(source='main_category.name', read_only=True)
    sub_category_name = serializers.CharField(source='sub_category.name', read_only=True)
    main_category_id = serializers.IntegerField(source='main_category.id', read_only=True)
    sub_category_id = serializers.IntegerField(source='sub_category.id', read_only=True)
    class Meta:
        model = Expense
        fields = [
            'id',
            'created_at',
            'main_category_name',
            'sub_category_name',
            'main_category_id',
            'sub_category_id',
            'amount',
            'note',
            'paid_from_safe'
        ]

class OtherIncomeCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = OtherIncomeCategory
        fields = ['id', 'name', 'description']

class OtherIncomeSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = OtherIncome
        fields = [
            'id',
            'date',
            'branch',
            'category',        # FK ID (writable)
            'category_name',   # Human-readable label (read-only)
            'amount',
            'note',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

class BankDepositSerializer(serializers.ModelSerializer):
    bank_name = serializers.CharField(source='bank_account.bank_name', read_only=True)
    account_number = serializers.CharField(source='bank_account.account_number', read_only=True)

    class Meta:
        model = BankDeposit
        fields = [
            'id',
            'branch',
            'bank_account',
            'bank_name',         # from FK (read-only)
            'account_number',    # from FK (read-only)
            'amount',
            'date',
            'is_confirmed',
            'note',
        ]
        read_only_fields = ['is_confirmed']

class BusSystemSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusSystemSetting
        fields = ['id', 'title', 'updated_at', 'is_active', ]
        read_only_fields = ['id', 'updated_at']

class FrameOnlyPatientInputSerializer(serializers.Serializer):
    name = serializers.CharField()
    phone_number = serializers.CharField()
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    nic = serializers.CharField(required=False, allow_null=True)
    address = serializers.CharField(required=False, allow_blank=True)
    patient_note = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        # Don't block on existing unique values — let service decide
        return data

class FrameOnlyOrderSerializer(serializers.Serializer):
    patient = FrameOnlyPatientInputSerializer()
    frame = serializers.PrimaryKeyRelatedField(queryset=Frame.objects.all())
    quantity = serializers.IntegerField(min_value=1)
    price_per_unit = serializers.DecimalField(max_digits=10, decimal_places=2)
    branch_id = serializers.IntegerField() 
    sales_staff_code = serializers.PrimaryKeyRelatedField(queryset=CustomUser.objects.all(), allow_null=True, required=False)
    payments = serializers.ListField(required=False, write_only=True)  

    status = serializers.CharField(required=False, default='pending')
    sub_total = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    discount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, default=0.00)
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    progress_status = serializers.ChoiceField(
    choices=[
        ('received_from_customer', 'Received from Customer'),
        ('issue_to_factory', 'Issued to Factory'),
        ('received_from_factory', 'Received from Factory'),
        ('issue_to_customer', 'Issued to Customer'),
    ],
    required=False,
    default='received_from_customer'
    )

    def validate(self, data):
        if not data.get('frame').is_active:
            raise serializers.ValidationError("Selected frame is inactive.")
        return data
    
class FrameOnlyOrderUpdateSerializer(serializers.Serializer):
    patient = FrameOnlyPatientInputSerializer(required=False)
    frame = serializers.PrimaryKeyRelatedField(queryset=Frame.objects.all())
    quantity = serializers.IntegerField(min_value=1)
    price_per_unit = serializers.DecimalField(max_digits=10, decimal_places=2)
    branch_id = serializers.IntegerField()
    sales_staff_code = serializers.IntegerField(required=False)
    payments = serializers.ListField(child=serializers.DictField(), required=False)

    status = serializers.CharField(required=False, default='pending')
    sub_total = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    discount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, default=0.00)
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)

    def validate(self, data):
        if not data.get('frame').is_active:
            raise serializers.ValidationError("Selected frame is inactive.")
        return data

class AppointmentTimeListSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source='patient.name', read_only=True)
    time = serializers.TimeField(format='%I:%M %p')  # Format time as 12-hour with AM/PM

    class Meta:
        model = Appointment
        fields = ['time', 'patient_name', 'channel_no']

class SingleRepaymentSerializer(serializers.Serializer):
    appointment_id = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    payment_method = serializers.ChoiceField(choices=ChannelPayment.PAYMENT_METHOD_CHOICES)
    is_final = serializers.BooleanField(required=False, default=False)

class MultipleRepaymentSerializer(serializers.Serializer):
    payments = SingleRepaymentSerializer(many=True)

class SafeBalanceSerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(source="branch.branch_name", read_only=True)

    class Meta:
        model = SafeBalance
        fields = [
            "id",
            "branch",
            "branch_name",
            "balance",
            "last_updated",
        ]
        read_only_fields = ["balance", "last_updated"]

class SafeTransactionSerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(source="branch.branch_name", read_only=True)
    transaction_type_display = serializers.CharField(source="get_transaction_type_display", read_only=True)

    class Meta:
        model = SafeTransaction
        fields = [
            "id",
            "branch",
            "branch_name",
            "transaction_type",
            "transaction_type_display",
            "amount",
            "reason",
            "reference_id",
            "date",
            "created_at",
        ]
        read_only_fields = ["date", "created_at"]

class DoctorClaimInvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = DoctorClaimInvoice
        fields = [
            "id",
            "invoice_number",
            "created_at",
            "branch",
        ]
        read_only_fields = ["created_at"]

class DoctorClaimChannelSerializer(serializers.ModelSerializer):
    doctor_name = serializers.CharField(source="doctor.name", read_only=True)
    class Meta:
        model = DoctorClaimChannel
        fields = [
            "id",
            "invoice_number",
            "created_at",
            "branch",
            "doctor",
            "doctor_name"
        ]
        read_only_fields = ["created_at"]

# serializers.py
class WhatsAppLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItemWhatsAppLog
        fields = ['id', 'status', 'created_at']
class ArrivalStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArrivalStatus
        fields = ['id', 'arrival_status', 'created_at']
class ExternalLensOrderItemSerializer(serializers.ModelSerializer):
    order_id = serializers.IntegerField(source='order.id', read_only=True)
    urgent = serializers.BooleanField(source='order.urgent', read_only=True)
    invoice_number = serializers.CharField(source='order.invoice.invoice_number', read_only=True)
    invoice_date = serializers.DateTimeField(source='order.invoice.invoice_date', read_only=True)
    branch_name = serializers.CharField(source='order.branch.branch_name', read_only=True)
    customer_name = serializers.CharField(source='order.customer.name', read_only=True)
    progress_status = serializers.SerializerMethodField()
    # progress_status = serializers.CharField(
    #     source='order.progress_status', read_only=True
    # )
    total_price = serializers.CharField(
        source='order.total_price', read_only=True
    )
    fitting_on_collection = serializers.BooleanField(
        source='order.fitting_on_collection', read_only=True
    )
    on_hold = serializers.BooleanField(
        source='order.on_hold', read_only=True
    )
    payments = serializers.SerializerMethodField()
    whatsapp_sent = serializers.SerializerMethodField()
    arrival_status = serializers.SerializerMethodField()
    class Meta:
        model = OrderItem
        fields = [
            'id', 'external_lens', 'quantity', 'price_per_unit', 'subtotal',
            'order_id', 'invoice_number', 'invoice_date', 'branch_name','customer_name',
            'total_price', 'fitting_on_collection', 'on_hold', 'payments','urgent',
            'progress_status','whatsapp_sent','arrival_status'
        ]
    def get_payments(self, obj):
            # Get the order related to this invoice
            order = obj.order
            if order:
                # Get all payments related to this order
                payments = order.orderpayment_set.all()
                # Serialize them
                from .serializers import OrderPaymentSerializer  # Avoid circular import if needed
                return OrderPaymentSerializer(payments, many=True).data
            return []
    def get_progress_status(self, obj):
        order = getattr(obj, "order", None)
        if not order:
            return None  # return None if order not present

        # Get the latest (last) progress status by changed_at DESCENDING
        last_status = order.order_progress_status.order_by('-changed_at').first()
        if last_status:
            return OrderProgressSerializer(last_status).data
        return None  # return None if there is no status
    
    def get_whatsapp_sent(self, obj):
        # Get the order related to this order item
        order = getattr(obj, "order", None)
        if not order:
            return None
                
        # Get the latest WhatsApp status log
        last_whatsapp_log = order.whatsapp_logs.order_by('-created_at').first()
        if last_whatsapp_log:
            return WhatsAppLogSerializer(last_whatsapp_log).data
        return None
    def get_arrival_status(self, obj):
        order = getattr(obj, "order", None)
        if not order:
            return None
        
        # Get the latest arrival status for this order
        last_arrival_status = ArrivalStatus.objects.filter(
            order=order,
            order__order_items__external_lens=obj.external_lens
        ).order_by('-created_at').first()
        
        if last_arrival_status:
            return ArrivalStatusSerializer(last_arrival_status).data
        return None
class SolderingOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = SolderingOrder
        fields = '__all__'

class SolderingInvoiceSerializer(serializers.ModelSerializer):
    order_details = serializers.SerializerMethodField()
    payments = serializers.SerializerMethodField()
    patient= serializers.SerializerMethodField()
    class Meta:
        model = SolderingInvoice
        fields = [
            "id",
            "invoice_number",
            "invoice_date",
            "order_id",
            "deleted_at",
            "is_deleted",
            "order_details",
            "payments",
            "patient"
        ]
    def get_order_details(self, obj):
        return SolderingOrderSerializer(obj.order).data
    
    def get_patient(self, obj):
        return PatientSerializer(obj.order.patient).data
    def get_payments(self, obj):
        # Get all payments for the linked order, and use your existing serializer
        payments_qs = obj.order.payments.filter(is_deleted=False).order_by('payment_date')
        return SolderingPaymentSerializer(payments_qs, many=True).data
    

class SolderingPaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = SolderingPayment
        fields = '__all__'

class SolderingRepaymentInputSerializer(serializers.Serializer):
    order_id = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    payment_method = serializers.ChoiceField(choices=[
        ('credit_card', 'Credit Card'),
        ('cash', 'Cash'),
        ('online_transfer', 'Online Transfer'),
    ])
    is_final_payment = serializers.BooleanField(default=False)

class OrderLiteSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    branch_name = serializers.CharField(source='branch.branch_name', read_only=True)
    issued_by_username = serializers.CharField(source='issued_by.username', read_only=True)
    invoice_number = serializers.CharField(source='invoice.invoice_number', read_only=True)
    #TODO: Add more fields as needed
    total_payment = serializers.SerializerMethodField(read_only=True)  # //TODO: Add total_payment field
    progress_status = serializers.SerializerMethodField()
    class Meta:
        model = Order
        fields = [
            'id',
            'customer_name',
            'branch_name',
            'order_date',
            'status',
            'progress_status',
            'total_price',
            'issued_by',
            'issued_by_username',
            'issued_date',
            'urgent',
            'invoice_number',
            'is_deleted',      # add this for "deactivated"
            'deleted_at',      # add this for "deactivation date"
            'is_refund',       # add this for refund status
            'refunded_at',     # add this for refund date
            'refund_note',     # add if you want the reason/note
            'total_payment'
           
        ]
    def get_total_payment(self, obj):
        # //TODO: Only sum payments that are not deleted and are successful
        return (
            obj.orderpayment_set.filter(is_deleted=False)
            .aggregate(total=models.Sum('amount'))['total'] or 0
        )
    def get_progress_status(self, obj):
        last_status = obj.order_progress_status.order_by('-changed_at').first()
        if last_status:
            return OrderProgressSerializer(last_status).data
        return None
class MntOrderSerializer(serializers.ModelSerializer):
    order_id = serializers.PrimaryKeyRelatedField(source='order', queryset=Order.objects.all())
    branch_id = serializers.PrimaryKeyRelatedField(source='branch', queryset=Branch.objects.all())
    branch_name = serializers.CharField(source='branch.branch_name', read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(source='user', queryset=CustomUser.objects.all(), allow_null=True)
    user_username = serializers.CharField(source='user.username', read_only=True)
    admin_id = serializers.PrimaryKeyRelatedField(source='admin', queryset=CustomUser.objects.all(), allow_null=True)
    admin_username = serializers.CharField(source='admin.username', read_only=True)
    invoice_number = serializers.CharField(source='order.invoice.invoice_number', read_only=True)
    order_total_price = serializers.CharField(source='order.total_price', read_only=True)
    class Meta:
        model = MntOrder
        fields = [
            'id',
            'mnt_number',
            'mnt_price',
            'order_id',
            'branch_id',
            'branch_name',
            'user_id',
            'user_username',
            'admin_id',
            'admin_username',
            'created_at',
            'invoice_number',
            'order_total_price'
        ]
        read_only_fields = ['mnt_number', 'created_at', 'branch_name', 'user_username', 'admin_username']

class FrameFilterSerializer(serializers.Serializer):
    brand = serializers.SerializerMethodField()
    brand_id = serializers.SerializerMethodField()
    code = serializers.SerializerMethodField()
    code_id = serializers.SerializerMethodField()
    frames = serializers.SerializerMethodField()

    def get_brand(self, obj):
        return obj['brand'].name if obj['brand'] else None
    
    def get_brand_id(self, obj):
        return obj['brand'].id if obj['brand'] else None
    
    def get_code(self, obj):
        return obj['code'].name if obj['code'] else None
    
    def get_code_id(self, obj):
        return obj['code'].id if obj['code'] else None

    def get_frames(self, obj):
        request = self.context.get('request')
        branch_id = request.query_params.get('branch_id') if request else None
        
        frames = []
        for frame in obj['frames']:
            frame_data = FrameSerializer(frame, context=self.context).data
            
            # Get stock information for the frame in the specified branch
            stock_data = None
            if branch_id:
                try:
                    stock = FrameStock.objects.filter(
                        frame=frame,
                        branch_id=branch_id
                    ).first()
                    if stock:
                        stock_data = {
                            'qty': stock.qty,
                            'initial_count': stock.initial_count,
                            'limit': stock.limit,
                            'branch_id': stock.branch_id
                        }
                except Exception as e:
                    print(f"Error getting stock for frame {frame.id}: {str(e)}")
            
            frame_data['stock'] = [stock_data]
            frames.append(frame_data)
            
        return frames