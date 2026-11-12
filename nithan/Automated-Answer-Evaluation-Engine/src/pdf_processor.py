import os
from typing import List, Union

import pymupdf  # PyMuPDF
from PIL import Image, ImageFilter, ImageOps


def preprocess_image(img: Image.Image) -> Image.Image:
    """
    Pre-process image for better OCR:
    - Convert to grayscale (L mode)
    - Apply contrast enhancement to make dark handwritten ink stand out
    """
    try:
        # Convert to grayscale (L mode)
        if img.mode != 'L':
            img = img.convert('L')
        
        # Apply contrast enhancement
        img = ImageOps.autocontrast(img, cutoff=2)
        
        # Try to use OpenCV if available for better binarization
        try:
            import cv2
            import numpy as np
            img_array = np.array(img)
            _, thresh = cv2.threshold(img_array, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            img = Image.fromarray(thresh)
        except Exception:
            img = img.filter(ImageFilter.SHARPEN)
            img = img.filter(ImageFilter.EDGE_ENHANCE_MORE)
        
        if img.mode != 'L':
            img = img.convert('L')
        
        return img
    except Exception:
        if img.mode != 'L':
            try:
                img = img.convert('L')
            except Exception:
                pass
        return img


def resize_if_needed(img: Image.Image, max_size: int = 2048) -> Image.Image:
    """
    Downscale image if max dimension > max_size to respect API limits
    while preserving handwriting clarity.
    """
    try:
        width, height = img.size
        max_dim = max(width, height)
        if max_dim > max_size:
            ratio = max_size / max_dim
            new_width = int(width * ratio)
            new_height = int(height * ratio)
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        return img
    except Exception:
        return img


def pdf_to_images(pdf_path: str, dpi: int = 300) -> List[Image.Image]:
    """
    Convert PDF pages to PIL images at specified DPI (minimum 300).
    Apply preprocessing and dimension checking/resizing.
    """
    if dpi < 300:
        dpi = 300
    
    images = []
    doc = pymupdf.open(pdf_path)
    try:
        zoom = dpi / 72.0
        matrix = pymupdf.Matrix(zoom, zoom)
        for page_num in range(len(doc)):
            page = doc[page_num]
            pix = page.get_pixmap(matrix=matrix)
            if pix.width == 0 or pix.height == 0:
                continue
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            img = preprocess_image(img)
            # Check dimensions and downscale if needed
            img = resize_if_needed(img, max_size=2048)
            images.append(img)
        if len(images) == 0 and len(doc) > 0:
            for page_num in range(len(doc)):
                page = doc[page_num]
                pix = page.get_pixmap(matrix=matrix)
                if pix.width > 0 and pix.height > 0:
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    img = preprocess_image(img)
                    img = resize_if_needed(img, max_size=2048)
                    images.append(img)
        return images
    finally:
        doc.close()


def load_image(image_path: str) -> List[Image.Image]:
    img = Image.open(image_path)
    img = preprocess_image(img)
    img = resize_if_needed(img, max_size=2048)
    return [img]


def process_file(file_path: str, dpi: int = 300) -> List[Image.Image]:
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    file_ext = os.path.splitext(file_path)[1].lower()
    if dpi < 300:
        dpi = 300
    
    if file_ext == '.pdf':
        return pdf_to_images(file_path, dpi=dpi)
    
    image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.gif', '.webp']
    if file_ext in image_extensions:
        return load_image(file_path)
    
    try:
        return pdf_to_images(file_path, dpi=dpi)
    except Exception:
        try:
            return load_image(file_path)
        except Exception as e:
            raise ValueError(f"Unsupported file format or corrupted file: {file_path}") from e


process_pdf_or_image = process_file
convert_pdf_to_images = pdf_to_images
load_pdf_or_image = process_file
