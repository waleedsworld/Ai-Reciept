import os
import uuid

RECEIPT_DIR = "storage/receipts/uploads"
os.makedirs(RECEIPT_DIR, exist_ok=True)


def save_receipt_image(file):
    receipt_id = str(uuid.uuid4())
    ext = os.path.splitext(file.filename)[1] or ".jpg"
    filename = f"{receipt_id}{ext}"
    path = os.path.join(RECEIPT_DIR, filename)
    file.save(path)
    return receipt_id, path