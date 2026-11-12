import os
import tempfile

import pymupdf 
from PIL import Image

from src import pdf_processor


def test_load_image():
    """Test loading a direct image file"""
    # Create a temporary image
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
        img = Image.new('RGB', (100, 100), color='red')
        img.save(tmp.name)
        tmp_path = tmp.name
    
    try:
        images = pdf_processor.process_file(tmp_path)
        assert isinstance(images, list)
        assert len(images) == 1
        assert isinstance(images[0], Image.Image)
    finally:
        os.unlink(tmp_path)


def test_pdf_to_images():
    """Test converting PDF to images at 300 DPI"""
    # Create a temporary PDF
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
        doc = pymupdf.open()
        page = doc.new_page(width=595, height=842)  # A4 size
        page.insert_text((50, 50), "Hello World")
        doc.save(tmp.name)
        doc.close()
        tmp_path = tmp.name
    
    try:
        images = pdf_processor.process_file(tmp_path)
        assert isinstance(images, list)
        assert len(images) >= 1
        assert isinstance(images[0], Image.Image)
        # At 300 DPI, A4 (595x842 pts) should be ~2480x3508 pixels
        assert images[0].width > 1000
        assert images[0].height > 1000
    finally:
        os.unlink(tmp_path)


def test_process_file_with_dpi():
    """Test process_file with custom DPI"""
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
        doc = pymupdf.open()
        page = doc.new_page(width=595, height=842)
        doc.save(tmp.name)
        doc.close()
        tmp_path = tmp.name
    
    try:
        images = pdf_processor.process_file(tmp_path, dpi=150)
        assert isinstance(images, list)
        assert len(images) >= 1
        assert isinstance(images[0], Image.Image)
    finally:
        os.unlink(tmp_path)
