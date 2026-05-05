"""Photo processing and Supabase Storage integration."""
import io
import os
from PIL import Image

MAX_DIMENSION = 600
WEBP_QUALITY = 75
BUCKET_NAME = 'part-photos'


def _get_supabase():
    from supabase import create_client
    url = os.environ.get('SUPABASE_URL', '')
    key = os.environ.get('SUPABASE_KEY', '')
    if not url or not key:
        return None
    return create_client(url, key)


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


def upload_photo(photo_bytes, filename):
    """Upload to Supabase Storage. Returns the public URL or None if not configured."""
    sb = _get_supabase()
    if not sb:
        return None

    path = f"parts/{filename}"
    sb.storage.from_(BUCKET_NAME).upload(
        path, photo_bytes,
        file_options={"content-type": "image/webp", "upsert": "true"}
    )
    return sb.storage.from_(BUCKET_NAME).get_public_url(path)


def delete_photo(filename):
    """Delete from Supabase Storage."""
    sb = _get_supabase()
    if not sb:
        return
    path = f"parts/{filename}"
    sb.storage.from_(BUCKET_NAME).remove([path])


def save_photo_local(photo_bytes, filename, upload_folder):
    """Fallback: save to local filesystem if Supabase isn't configured."""
    filepath = os.path.join(upload_folder, filename)
    with open(filepath, 'wb') as f:
        f.write(photo_bytes)
