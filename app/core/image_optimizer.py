import io
from PIL import Image, ImageOps
from pillow_heif import register_heif_opener

# Register HEIF opener with Pillow to support iPhone HEIC images
register_heif_opener()

def optimize_image(file_data: bytes, max_width: int = 1600, max_height: int = 1600, quality: int = 80) -> tuple[bytes, str]:
    """
    Optimizes an image by:
    1. Transposing based on EXIF orientation (preventing rotation issues).
    2. Resizing within max bounding box while preserving aspect ratio.
    3. Stripping EXIF/Metadata.
    4. Converting to modern WebP format.
    
    Returns:
        tuple: (optimized_image_bytes, "image/webp")
    """
    try:
        img = Image.open(io.BytesIO(file_data))
    except Exception:
        # Fallback if image opening fails
        return file_data, "image/jpeg"
        
    # Correct orientation based on EXIF tags before stripping them
    img = ImageOps.exif_transpose(img)
    
    # Handle color modes
    if img.mode in ("CMYK", "P"):
        img = img.convert("RGB")
        
    # Resize keeping aspect ratio if larger than boundaries
    width, height = img.size
    if width > max_width or height > max_height:
        ratio = min(max_width / width, max_height / height)
        new_size = (int(width * ratio), int(height * ratio))
        img = img.resize(new_size, Image.Resampling.LANCZOS)
        
    # Compress and save to WebP in memory
    out_io = io.BytesIO()
    # method=6 provides the highest compression efficiency (slowest encode, smallest file)
    img.save(out_io, format="WEBP", quality=quality, method=6)
    optimized_bytes = out_io.getvalue()
    
    return optimized_bytes, "image/webp"
