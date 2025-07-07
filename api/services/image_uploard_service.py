# utils/image_utils.py
from PIL import Image
from io import BytesIO
from django.core.files.base import ContentFile

def compress_image_to_webp(image_field, quality=85):
    # //TODO: Handle None/image_field not image edge case
    if not image_field or not hasattr(image_field, 'file'):
        return None

    try:
        # Open image
        img = Image.open(image_field)
        img = img.convert('RGB')  # WebP does not support RGBA by default

        # Compress and convert to webp
        buffer = BytesIO()
        img.save(buffer, format='WEBP', quality=quality)
        file_name = image_field.name.rsplit('.', 1)[0] + '.webp'
        return ContentFile(buffer.getvalue(), name=file_name)
    except Exception as e:
        # //TODO: Log error and handle exception for compliance
        return image_field  # fallback: return original file
