"""Image export utilities - download M Number folders as ZIP."""
import io
import zipfile
import logging
from pathlib import Path

from image_generator import generate_all_images_for_product
from jobs import Job


def generate_images_zip(products: list[dict]) -> bytes:
    """
    Generate a ZIP file containing all product images organized by M Number.
    
    Args:
        products: List of product dicts
    
    Returns:
        ZIP file as bytes
    """
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for product in products:
            m_number = product.get("m_number", "UNKNOWN")
            
            try:
                images = generate_all_images_for_product(product)
                
                for img_type, png_bytes in images.items():
                    # Add PNG to ZIP
                    zf.writestr(f"{m_number}/{m_number}_{img_type}.png", png_bytes)
                    
                    # Also add JPEG version
                    from PIL import Image
                    from io import BytesIO
                    
                    img = Image.open(BytesIO(png_bytes))
                    if img.mode == "RGBA":
                        background = Image.new("RGB", img.size, (255, 255, 255))
                        background.paste(img, mask=img.split()[3])
                        img = background
                    elif img.mode != "RGB":
                        img = img.convert("RGB")
                    
                    jpeg_buffer = BytesIO()
                    img.save(jpeg_buffer, format="JPEG", quality=95)
                    zf.writestr(f"{m_number}/{m_number}_{img_type}.jpg", jpeg_buffer.getvalue())
                    
            except Exception as e:
                logging.error(f"Failed to generate images for {m_number}: {e}")
                # Add error file to ZIP
                zf.writestr(f"{m_number}/ERROR.txt", f"Failed to generate images: {e}")
    
    zip_buffer.seek(0)
    return zip_buffer.getvalue()


def generate_single_product_zip(product: dict) -> bytes:
    """
    Generate a ZIP file for a single product's images.
    
    Args:
        product: Product dict
    
    Returns:
        ZIP file as bytes
    """
    return generate_images_zip([product])


def generate_images_zip_job(job: Job, products: list[dict]) -> bytes:
    """
    Background job to generate images ZIP.
    
    Args:
        job: Job object for progress updates
        products: List of product dicts
    
    Returns:
        ZIP file as bytes
    """
    job.total = len(products)
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for i, product in enumerate(products):
            m_number = product.get("m_number", "UNKNOWN")
            job.message = f"Generating images for {m_number}..."
            job.progress = i
            
            try:
                images = generate_all_images_for_product(product)
                
                for img_type, png_bytes in images.items():
                    zf.writestr(f"{m_number}/{m_number}_{img_type}.png", png_bytes)
                    
                    # Also add JPEG
                    from PIL import Image
                    from io import BytesIO
                    
                    img = Image.open(BytesIO(png_bytes))
                    if img.mode == "RGBA":
                        background = Image.new("RGB", img.size, (255, 255, 255))
                        background.paste(img, mask=img.split()[3])
                        img = background
                    elif img.mode != "RGB":
                        img = img.convert("RGB")
                    
                    jpeg_buffer = BytesIO()
                    img.save(jpeg_buffer, format="JPEG", quality=95)
                    zf.writestr(f"{m_number}/{m_number}_{img_type}.jpg", jpeg_buffer.getvalue())
                    
            except Exception as e:
                logging.error(f"Failed to generate images for {m_number}: {e}")
                zf.writestr(f"{m_number}/ERROR.txt", f"Failed to generate images: {e}")
    
    job.progress = job.total
    job.message = f"Generated ZIP for {len(products)} products"
    
    zip_buffer.seek(0)
    return zip_buffer.getvalue()
