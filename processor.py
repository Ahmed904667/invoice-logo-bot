import io
from pathlib import Path
from typing import Optional, Tuple, Union
import pymupdf
from PIL import Image


class InvoiceProcessingError(Exception):
    """Custom exception raised when invoice processing encounters an error."""
    pass


def load_bytes(source: Union[bytes, str, Path]) -> bytes:
    """Helper to convert file path or bytes into bytes."""
    if isinstance(source, bytes):
        return source
    path = Path(source)
    if not path.exists():
        raise InvoiceProcessingError(f"File not found: {path}")
    return path.read_bytes()


def is_pdf(source: Union[bytes, str, Path]) -> bool:
    """Check if the source represents a PDF document."""
    if isinstance(source, (str, Path)):
        p = Path(source)
        if p.suffix.lower() == ".pdf":
            return True
        if p.exists():
            try:
                with pymupdf.open(str(p)) as doc:
                    return bool(doc.is_pdf and len(doc) > 0)
            except Exception:
                return False
    elif isinstance(source, (bytes, bytearray)):
        data = bytes(source)
        if b"%PDF" in data[:1024]:
            try:
                with pymupdf.open(stream=data) as doc:
                    return bool(doc.is_pdf and len(doc) > 0)
            except Exception:
                return False
        return False
    return False


def add_background_to_pdf(
    input_pdf: Union[bytes, str, Path],
    bg_source: Union[bytes, str, Path],
    output_path: Optional[Union[str, Path]] = None,
    dpi_preview: int = 150
) -> Tuple[bytes, bytes]:
    """
    Stamps the background (image or PDF letterhead) onto all pages of the input PDF.
    
    Args:
        input_pdf: PDF file as bytes, file path string, or Path object.
        bg_source: Background image or PDF as bytes, file path string, or Path object.
        output_path: Optional file path to save the resulting PDF.
        dpi_preview: DPI resolution for the generated first-page PNG preview.
        
    Returns:
        Tuple of (output_pdf_bytes, preview_png_bytes)
    """
    pdf_bytes = load_bytes(input_pdf)
    bg_bytes = load_bytes(bg_source)

    try:
        doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    except Exception as e:
        raise InvoiceProcessingError(f"Failed to open PDF document: {e}")

    if doc.is_encrypted:
        raise InvoiceProcessingError("The uploaded PDF is password protected / encrypted.")

    if len(doc) == 0:
        raise InvoiceProcessingError("The uploaded PDF has no pages.")

    bg_is_pdf = is_pdf(bg_bytes)

    if bg_is_pdf:
        try:
            bg_doc = pymupdf.open(stream=bg_bytes, filetype="pdf")
        except Exception as e:
            doc.close()
            raise InvoiceProcessingError(f"Failed to open background PDF: {e}")

        if len(bg_doc) == 0:
            bg_doc.close()
            doc.close()
            raise InvoiceProcessingError("The background PDF has no pages.")

        try:
            for i, page in enumerate(doc):
                bg_pno = i if i < len(bg_doc) else 0
                page.show_pdf_page(page.rect, bg_doc, pno=bg_pno, keep_proportion=False, overlay=False)
        except Exception as e:
            bg_doc.close()
            doc.close()
            raise InvoiceProcessingError(f"Failed to apply PDF background: {e}")
        bg_doc.close()
    else:
        # Apply background image behind existing content for each page
        try:
            for page in doc:
                # overlay=False puts the image behind existing drawings/text
                page.insert_image(page.rect, stream=bg_bytes, overlay=False)
        except Exception as e:
            doc.close()
            raise InvoiceProcessingError(f"Failed to apply background image: {e}")

    # Generate first-page preview as PNG
    try:
        first_page = doc[0]
        pix = first_page.get_pixmap(dpi=dpi_preview)
        preview_bytes = pix.tobytes("png")
    except Exception:
        preview_bytes = b""

    # Save to bytes
    try:
        out_pdf_bytes = doc.tobytes(deflate=True, garbage=3)
    except Exception as e:
        doc.close()
        raise InvoiceProcessingError(f"Failed to generate output PDF: {e}")

    doc.close()

    if output_path:
        out_path = Path(output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(out_pdf_bytes)

    return out_pdf_bytes, preview_bytes


def add_background_to_image(
    input_image: Union[bytes, str, Path],
    bg_source: Union[bytes, str, Path],
    output_path: Optional[Union[str, Path]] = None,
    dpi_preview: int = 150
) -> Tuple[bytes, bytes]:
    """
    Overlays an image invoice onto the company letterhead template (PDF or Image),
    returning a PDF and PNG preview.
    
    Args:
        input_image: Image file as bytes, file path string, or Path object.
        bg_source: Background image or PDF as bytes, file path string, or Path object.
        output_path: Optional file path to save the resulting PDF.
        dpi_preview: DPI resolution for preview.
        
    Returns:
        Tuple of (output_pdf_bytes, preview_png_bytes)
    """
    img_bytes = load_bytes(input_image)
    bg_bytes = load_bytes(bg_source)

    try:
        # Open input invoice image
        inv_pil = Image.open(io.BytesIO(img_bytes)).convert("RGBA")
        inv_buffer = io.BytesIO()
        inv_pil.save(inv_buffer, format="PNG")
        inv_png_bytes = inv_buffer.getvalue()

        bg_is_pdf = is_pdf(bg_bytes)
        if bg_is_pdf:
            bg_doc = pymupdf.open(stream=bg_bytes, filetype="pdf")
            if len(bg_doc) == 0:
                bg_doc.close()
                raise InvoiceProcessingError("The background PDF has no pages.")
            doc = pymupdf.open()
            doc.insert_pdf(bg_doc, from_page=0, to_page=0)
            bg_doc.close()
            page = doc[0]
        else:
            # Inspect background dimensions using PIL
            bg_pil = Image.open(io.BytesIO(bg_bytes))
            bg_w, bg_h = bg_pil.size
            pt_w = 595.0  # Standard A4 width in points
            pt_h = pt_w * (bg_h / bg_w)
            doc = pymupdf.open()
            page = doc.new_page(width=pt_w, height=pt_h)
            page.insert_image(page.rect, stream=bg_bytes)

        # Center bounds with some padding
        pad_x = page.rect.width * 0.05
        pad_y = page.rect.height * 0.15
        target_rect = pymupdf.Rect(pad_x, pad_y, page.rect.width - pad_x, page.rect.height - pad_y)
        page.insert_image(target_rect, stream=inv_png_bytes, overlay=True)

        # Render preview
        pix = page.get_pixmap(dpi=dpi_preview)
        preview_bytes = pix.tobytes("png")

        out_pdf_bytes = doc.tobytes(deflate=True, garbage=3)
        doc.close()

        if output_path:
            out_path = Path(output_path)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_bytes(out_pdf_bytes)

        return out_pdf_bytes, preview_bytes
    except Exception as e:
        if isinstance(e, InvoiceProcessingError):
            raise
        raise InvoiceProcessingError(f"Failed to process image invoice: {e}")


def get_preview_from_pdf(pdf_source: Union[bytes, str, Path], page_num: int = 0, dpi: int = 150) -> bytes:
    """Extract a PNG preview of a specific page from a PDF."""
    pdf_bytes = load_bytes(pdf_source)
    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    if page_num >= len(doc):
        page_num = 0
    page = doc[page_num]
    pix = page.get_pixmap(dpi=dpi)
    png_bytes = pix.tobytes("png")
    doc.close()
    return png_bytes


def get_background_preview(bg_source: Union[bytes, str, Path], dpi: int = 150) -> bytes:
    """Generate a PNG preview of the background, whether it is a PDF or an Image."""
    bg_bytes = load_bytes(bg_source)
    if is_pdf(bg_bytes):
        return get_preview_from_pdf(bg_bytes, page_num=0, dpi=dpi)
    else:
        try:
            im = Image.open(io.BytesIO(bg_bytes))
            buf = io.BytesIO()
            im.save(buf, format="PNG")
            return buf.getvalue()
        except Exception:
            return bg_bytes
