from rest_framework import serializers
from .models import Branch, Refraction,RefractionDetails,Brand,Color,Code,Frame,FrameStock

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