import os
import uuid

from werkzeug.utils import secure_filename

RECEIPT_DIR = "storage/receipts/uploads"
os.makedirs(RECEIPT_DIR, exist_ok=True)

# Only accept image types the vision parser can actually read. Anything else is
# rejected up front rather than saved and handed to the model.
ALLOWED_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".heic", ".heif"}


class UnsupportedFileType(ValueError):
    """Raised when an upload has an extension we don't accept."""


def _safe_extension(filename):
    """Return a normalised, whitelisted extension for *filename*.

    Guards against the surprises real uploads throw at us:
      * ``filename`` being ``None`` or empty (some clients omit it entirely),
      * path-traversal or odd characters in the name (``secure_filename``),
      * unexpected / dangerous extensions (rejected via the allow-list).
    """
    name = secure_filename(filename or "")
    ext = os.path.splitext(name)[1].lower()
    if not ext:
        # No usable extension — default to .jpg so the file is still storable.
        return ".jpg"
    if ext not in ALLOWED_EXTS:
        raise UnsupportedFileType(
            f"Unsupported file type '{ext}'. "
            f"Allowed: {', '.join(sorted(ALLOWED_EXTS))}"
        )
    return ext


def save_receipt_image(file):
    """Persist an uploaded receipt image under a random UUID filename.

    The stored name is derived only from a fresh UUID plus a validated
    extension, so a caller can never influence the on-disk path.
    """
    receipt_id = str(uuid.uuid4())
    ext = _safe_extension(getattr(file, "filename", None))
    filename = f"{receipt_id}{ext}"
    path = os.path.join(RECEIPT_DIR, filename)
    file.save(path)
    return receipt_id, path
