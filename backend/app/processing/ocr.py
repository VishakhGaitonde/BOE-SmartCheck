import fitz
import pytesseract
from PIL import Image
import io

pytesseract.pytesseract.tesseract_cmd = r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe"


def ocr_pdf_pages(filepath: str) -> list[str]:
    doc = fitz.open(filepath)
    pages_text = []

    for page in doc:
        pix = page.get_pixmap(dpi=200)
        img_bytes = pix.tobytes("png")
        image = Image.open(io.BytesIO(img_bytes))
        pages_text.append(pytesseract.image_to_string(image))

    doc.close()
    return pages_text


def ocr_pdf(filepath: str) -> str:
    return "\n".join(ocr_pdf_pages(filepath)).strip()