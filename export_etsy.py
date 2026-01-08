"""Etsy Shop Uploader export generator.

Generates Etsy Shop Uploader compatible XLSX from product database.
"""
import io
import logging
from typing import Optional

import openpyxl

# Size mappings
SIZE_CONFIG = {
    "dracula": {"display": "95mm x 95mm", "price": 10.99, "code": "XS"},
    "saville": {"display": "110mm x 95mm", "price": 11.99, "code": "S"},
    "dick": {"display": "140mm x 90mm", "price": 12.99, "code": "M"},
    "barzan": {"display": "190mm x 140mm", "price": 15.99, "code": "L"},
    "baby_jesus": {"display": "290mm x 190mm", "price": 17.99, "code": "XL"},
}

# Color mappings
COLOR_DISPLAY = {
    "silver": "Silver",
    "gold": "Gold",
    "white": "White",
}

# Shop Uploader configuration
SHOP_UPLOADER_CONFIG = {
    "category": "Signs (2844)",
    "shipping_profile": "Postage 2025",
    "return_policy": "30 Day Returns",
}

# Shop Uploader columns
SHOP_UPLOADER_COLUMNS = [
    "listing_id",
    "parent_sku",
    "sku",
    "title",
    "description",
    "price",
    "quantity",
    "category",
    "_primary_color",
    "_secondary_color",
    "tags",
    "materials",
    "image1",
    "image2",
    "image3",
    "image4",
    "image5",
    "variation_option1_name",
    "variation_option1_value",
    "variation_option2_name",
    "variation_option2_value",
    "shipping_profile",
    "return_policy",
    "processing_time",
]


def generate_etsy_xlsx(products: list[dict], r2_public_url: str = "") -> bytes:
    """
    Generate Etsy Shop Uploader compatible XLSX.
    
    Args:
        products: List of product dicts from database
        r2_public_url: Base URL for R2 images
    
    Returns:
        XLSX file as bytes
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Template"
    
    # Write headers
    for col, header in enumerate(SHOP_UPLOADER_COLUMNS, 1):
        ws.cell(row=1, column=col, value=header)
    
    row_num = 2
    
    # Group products by parent (description)
    parent_groups = {}
    for product in products:
        desc = product.get("description", "Unknown")
        if desc not in parent_groups:
            parent_groups[desc] = []
        parent_groups[desc].append(product)
    
    for desc, group in parent_groups.items():
        # Use first product's m_number as parent SKU
        parent_sku = group[0].get("m_number", "")
        
        for product in group:
            m_number = product.get("m_number", "")
            size = product.get("size", "dracula").lower()
            color = product.get("color", "silver").lower()
            
            size_info = SIZE_CONFIG.get(size, SIZE_CONFIG["dracula"])
            color_display = COLOR_DISPLAY.get(color, "Silver")
            
            # Build title (max 140 chars for Etsy)
            title = f"{desc} Sign - {size_info['display']} Brushed Aluminium - {color_display}"
            if len(title) > 140:
                title = title[:137] + "..."
            
            # Build description
            description = f"""{desc}

Premium quality brushed aluminium sign with UV-resistant printing.

SPECIFICATIONS:
• Size: {size_info['display']}
• Material: 1mm Brushed Aluminium
• Finish: {color_display}
• Mounting: Self-adhesive backing (peel and stick)
• Weatherproof and UV resistant
• Rounded corners for safety

Perfect for offices, warehouses, shops, and public spaces.

SHIPPING:
Free UK delivery. Dispatched within 1-3 business days.
"""
            
            # Image URLs
            images = []
            if r2_public_url:
                for img_type in ["main", "dimensions", "peel_and_stick", "rear"]:
                    images.append(f"{r2_public_url}/{m_number}/{m_number}_{img_type}.jpg")
            
            # Tags (comma-separated, max 13)
            tags = f"{desc.lower()},sign,aluminium sign,safety sign,{color_display.lower()} sign,office sign,warehouse sign,self adhesive sign,weatherproof sign,uk sign"
            
            row_data = {
                "listing_id": "",
                "parent_sku": parent_sku,
                "sku": m_number,
                "title": title,
                "description": description,
                "price": size_info["price"],
                "quantity": 10,
                "category": SHOP_UPLOADER_CONFIG["category"],
                "_primary_color": color_display,
                "_secondary_color": "",
                "tags": tags,
                "materials": "Aluminium",
                "image1": images[0] if len(images) > 0 else "",
                "image2": images[1] if len(images) > 1 else "",
                "image3": images[2] if len(images) > 2 else "",
                "image4": images[3] if len(images) > 3 else "",
                "image5": "",
                "variation_option1_name": "Size",
                "variation_option1_value": size_info["display"],
                "variation_option2_name": "Colour",
                "variation_option2_value": color_display,
                "shipping_profile": SHOP_UPLOADER_CONFIG["shipping_profile"],
                "return_policy": SHOP_UPLOADER_CONFIG["return_policy"],
                "processing_time": "1-3 business days",
            }
            
            for col, header in enumerate(SHOP_UPLOADER_COLUMNS, 1):
                ws.cell(row=row_num, column=col, value=row_data.get(header, ""))
            
            row_num += 1
    
    # Save to bytes
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output.getvalue()


if __name__ == "__main__":
    # Test
    test_products = [
        {"m_number": "M1001", "description": "No Entry", "size": "saville", "color": "silver"},
        {"m_number": "M1002", "description": "No Entry", "size": "dick", "color": "gold"},
        {"m_number": "M1003", "description": "Staff Only", "size": "saville", "color": "white"},
    ]
    xlsx_bytes = generate_etsy_xlsx(test_products)
    with open("test_etsy.xlsx", "wb") as f:
        f.write(xlsx_bytes)
    print(f"Generated test_etsy.xlsx ({len(xlsx_bytes)} bytes)")
