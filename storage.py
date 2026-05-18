"""Photo processing and local photo storage."""
import io
import os
from PIL import Image

MAX_DIMENSION = 600
WEBP_QUALITY = 75


def process_image(file_stream):
    """Resize to 600px max and convert to WebP. Returns (bytes, filename_ext)."""
    img = Image.open(file_stream)
    if img.mode in ('RGBA', 'P'):
        img = img.convert('RGB')

    w, h = img.size
    if max(w, h) > MAX_DIMENSION:
        ratio = MAX_DIMENSION / max(w, h)
        img = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, format='WEBP', quality=WEBP_QUALITY)
    buf.seek(0)
    return buf.getvalue()


def save_photo_local(photo_bytes, filename, upload_folder):
    """Save processed photo bytes under the local upload folder."""
    os.makedirs(upload_folder, exist_ok=True)
    filepath = os.path.join(upload_folder, filename)
    with open(filepath, 'wb') as f:
        f.write(photo_bytes)


def delete_photo_local(filename, upload_folder):
    """Delete a locally stored photo if it exists."""
    filepath = os.path.join(upload_folder, filename)
    if os.path.exists(filepath):
        os.remove(filepath)
