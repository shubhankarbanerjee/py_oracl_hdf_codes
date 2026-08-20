import pytesseract
from PIL import Image
import pandas as pd

# Load the images
image_paths = ["C:\\git\\12_2.jpeg" ] #, "/mnt/data/12_2.jpeg"]
extracted_texts = []

# Extract text using OCR
for path in image_paths:
    img = Image.open(path)
    text = pytesseract.image_to_string(img)
    extracted_texts.append(text)

# Combine extracted text
extracted_text = "\n".join(extracted_texts)
extracted_text[:1000]  # Previewing the first 1000 characters for verification
