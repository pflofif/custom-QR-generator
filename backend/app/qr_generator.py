import io
import os
import base64
import asyncio
import tempfile
import qrcode
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers.pil import RoundedModuleDrawer
from PIL import Image

# ── Pillow 10+ compatibility shim for amzqr (which uses Image.ANTIALIAS) ─────
try:
    if not hasattr(Image, "ANTIALIAS"):
        Image.ANTIALIAS = Image.LANCZOS  # type: ignore[attr-defined]
except Exception:
    pass


def generate_qr_base64(url: str, box_size: int = 10, border: int = 4) -> str:
    """Generate a QR code PNG and return it as a base64-encoded data URI."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=box_size,
        border=border,
    )
    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image(
        image_factory=StyledPilImage,
        module_drawer=RoundedModuleDrawer(),
        back_color="white",
        fill_color="#0f172a",
    )

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    encoded = base64.b64encode(buffer.read()).decode("utf-8")
    return f"data:image/png;base64,{encoded}"


def generate_qr_bytes(url: str, box_size: int = 10, border: int = 4) -> bytes:
    """Return raw PNG bytes for the QR code."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=box_size,
        border=border,
    )
    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image(
        image_factory=StyledPilImage,
        module_drawer=RoundedModuleDrawer(),
        back_color="white",
        fill_color="#0f172a",
    )

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer.read()


# ── amzqr-based custom QR generator ──────────────────────────────────────────

async def generate_amazing_qr_bytes(
    url: str,
    background_bytes: bytes | None = None,
    background_ext: str = ".png",
    colorized: bool = False,
    contrast: float = 1.0,
    brightness: float = 1.0,
    version: int = 1,
    level: str = "H",
) -> tuple[bytes, str]:
    """
    Generate a custom QR code via amzqr and return (image_bytes, mime_type).
    Runs the synchronous amzqr.run() in a thread pool to avoid blocking the loop.
    """
    def _run() -> tuple[bytes, str]:
        from amzqr import amzqr as _amzqr
        with tempfile.TemporaryDirectory() as tmp:
            bg_path: str | None = None
            if background_bytes:
                bg_fname = f"bg{background_ext}"
                bg_path = os.path.join(tmp, bg_fname)
                with open(bg_path, "wb") as fh:
                    fh.write(background_bytes)

            is_gif = background_ext.lower() == ".gif"
            out_name = "output.gif" if is_gif else "output.png"
            mime = "image/gif" if is_gif else "image/png"

            _amzqr.run(
                url,
                version=version,
                level=level,
                picture=bg_path,
                colorized=colorized if bg_path else False,
                contrast=contrast,
                brightness=brightness,
                save_name=out_name,
                save_dir=tmp,
            )

            out_path = os.path.join(tmp, out_name)
            with open(out_path, "rb") as fh:
                return fh.read(), mime

    return await asyncio.to_thread(_run)
