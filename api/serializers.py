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
    Doctor
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
            'refraction',
            'hb_rx_right', 'hb_rx_left',
            'auto_ref', 'ntc', 'va_without_glass',
            'va_without_ph', 'va_with_glass',
            'right_eye_dist_sph', 'right_eye_dist_cyl', 'right_eye_dist_axis',
            'right_eye_near_sph',
            'left_eye_dist_sph', 'left_eye_dist_cyl', 'left_eye_dist_axis',
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
        fields = ['id', 'name', 'specialization', 'contact_info', 'status']