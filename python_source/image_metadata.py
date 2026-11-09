"""This file is image_metadata.py and its job is to read hidden details inside picture files.
It finds the image format, width and height in pixels, megapixels, and camera EXIF notes
like which phone or camera took the photo and the date it was taken.
If a picture has no camera info or is broken, this code handles it safely without crashing.
"""
from math import gcd

# Try to load the Pillow image library, or set it to None if it is not installed yet
try:
    from PIL import Image
except ImportError:
    Image = None

# Standard code numbers that digital cameras use to store hidden EXIF notes inside a photo
EXIF_MAKE = 271
EXIF_MODEL = 272
EXIF_ORIENTATION = 274
EXIF_SOFTWARE = 305
EXIF_DATETIME = 306
EXIF_IFD = 0x8769        # Section that holds the original capture date and camera settings
EXIF_EXPOSURE_TIME = 33434
EXIF_FNUMBER = 33437
EXIF_ISO = 34855
EXIF_DATETIME_ORIGINAL = 36867
EXIF_FOCAL_LENGTH = 37386
EXIF_LENS_MODEL = 42036
GPS_IFD = 0x8825         # Section that tells us if GPS map coordinates were saved


def _clean_date(text):
    """Cameras often save dates with colons like 2025:12:18, so this turns it into 2025-12-18."""
    text = str(text).strip()
    if len(text) >= 10 and text[4] == ":" and text[7] == ":":
        return text[:4] + "-" + text[5:7] + "-" + text[8:]
    return text


def _format_float(val):
    """Safely turns an EXIF fraction or number into a clean decimal number."""
    try:
        return round(float(val), 2)
    except Exception:
        return None


def read_image_metadata(path):
    """Opens an image file and reads its width, height, megapixels, aspect ratio, color mode,
    and rich camera EXIF info (camera model, capture date, lens, ISO, aperture, shutter speed,
    focal length, and GPS presence).
    If the file is not a valid image, it sets ok to False so the app knows it could not be read."""
    info = {"ok": False}
    if Image is None:
        info["error"] = "Pillow is not installed"
        return info

    try:
        with Image.open(path) as img:
            width, height = img.size
            # Use the greatest common divisor (gcd) to simplify width and height into a ratio like 16:9
            divisor = gcd(width, height) or 1
            info.update(
                ok=True,
                format=img.format or "Unknown",
                mode=img.mode or "RGB",
                width=width,
                height=height,
                megapixels=round(width * height / 1_000_000, 2),
                aspect=f"{width // divisor}:{height // divisor}",
                exif=False,
                camera=None,
                captured=None,
                lens=None,
                iso=None,
                aperture=None,
                shutter=None,
                focal_length=None,
                software=None,
                gps=False,
            )

            # Now try to read the hidden EXIF camera tags from the image
            try:
                exif = img.getexif()
            except Exception:
                exif = None

            if exif:
                info["exif"] = True
                # Combine the camera brand name and camera model name together
                camera = f"{exif.get(EXIF_MAKE, '')} {exif.get(EXIF_MODEL, '')}".strip()
                info["camera"] = camera or None
                software = str(exif.get(EXIF_SOFTWARE, "")).strip()
                info["software"] = software or None

                # Read detailed camera settings from the EXIF sub-table
                sub_ifd = {}
                try:
                    sub_ifd = exif.get_ifd(EXIF_IFD) or {}
                except Exception:
                    sub_ifd = {}

                # Find the exact date and time when the photo was snapped
                captured = sub_ifd.get(EXIF_DATETIME_ORIGINAL) or exif.get(EXIF_DATETIME)
                info["captured"] = _clean_date(captured) if captured else None

                # Read richer camera exposure settings if the camera recorded them
                lens = str(sub_ifd.get(EXIF_LENS_MODEL, "")).strip()
                info["lens"] = lens or None

                iso_val = sub_ifd.get(EXIF_ISO)
                if iso_val:
                    info["iso"] = f"ISO {iso_val}"

                fnum = _format_float(sub_ifd.get(EXIF_FNUMBER))
                if fnum:
                    info["aperture"] = f"f/{fnum}"

                exp = _format_float(sub_ifd.get(EXIF_EXPOSURE_TIME))
                if exp:
                    if 0 < exp < 1:
                        info["shutter"] = f"1/{max(1, int(round(1.0 / exp)))} sec"
                    else:
                        info["shutter"] = f"{exp} sec"

                focal = _format_float(sub_ifd.get(EXIF_FOCAL_LENGTH))
                if focal:
                    info["focal_length"] = f"{focal} mm"

                # Check if the photo has GPS location data attached to it
                try:
                    info["gps"] = bool(exif.get_ifd(GPS_IFD))
                except Exception:
                    info["gps"] = False
    except Exception as error:
        info["ok"] = False
        info["error"] = str(error)

    return info


# If you run this file from the command line with a photo path, it prints the photo details
if __name__ == "__main__":
    import sys
    for given in sys.argv[1:]:
        print(given, read_image_metadata(given))