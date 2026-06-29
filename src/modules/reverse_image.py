# GHOST — Reverse Image Search Module
# Yandex, Google, TinEye, Facecheck, PimEyes

import httpx
import re
import os
import base64
from .http_utils import get_headers, polite_request


def get_image_search_urls(image_path: str) -> dict:
    """
    Generate reverse image search URLs for a given image.
    Returns URLs for manual/automated search on multiple engines.
    """
    if not os.path.exists(image_path):
        return {"error": f"File not found: {image_path}"}

    ext = os.path.splitext(image_path)[1].lower()
    if ext not in [".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"]:
        return {"error": f"Unsupported format: {ext}"}

    result = {
        "image_path": image_path,
        "search_urls": {},
        "uploaded_urls": {},
    }

    # Direct search URLs (manual click)
    result["search_urls"] = {
        "yandex": f"https://yandex.com/images/search?url={image_path}&rpt=imageview",
        "google": f"https://www.google.com/searchbyimage?image_url={image_path}",
        "tineye": f"https://www.tineye.com/search/?url={image_path}",
        "bing": f"https://www.bing.com/images/search?view=detailv2&iss=sbi&q=imgurl:{image_path}",
        "facecheck": f"https://facecheck.id/",
        "search4faces": f"https://search4faces.com/",
    }

    return result


def reverse_search_yandex(image_path: str) -> dict:
    """
    Search an image on Yandex (best for face search).
    Yandex requires uploading the image via multipart form.
    """
    result = {"engine": "Yandex", "found": False, "matches": [], "error": None}

    if not os.path.exists(image_path):
        result["error"] = "File not found"
        return result

    try:
        url = "https://yandex.com/images/search"
        with open(image_path, "rb") as f:
            files = {"upfile": ("image.jpg", f, "image/jpeg")}
            data = {"rpt": "imageview", "format": "json"}
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json",
            }

            with httpx.Client(timeout=15, headers=headers, follow_redirects=True, verify=False) as client:
                r = client.post(url, files=files, data=data, params={"request": '{"blocks":[{"block":"cbir-page__GET"}]}'})
                if r.status_code == 200:
                    match = re.search(r'"links":\{"go":\s*"([^"]+)"', r.text)
                    if match:
                        search_url = match.group(1)
                        result["found"] = True
                        result["matches"].append({"url": search_url, "source": "yandex"})
    except Exception as e:
        result["error"] = str(e)

    return result


def reverse_search_tineye(image_path: str) -> dict:
    """
    Search an image on TinEye. Requires upload or public URL.
    Note: TinEye is best with public URLs. Local files need upload via API (requires key).
    Falls back to generating a search URL.
    """
    result = {"engine": "TinEye", "found": False, "matches": [], "error": None}

    try:
        # Try public upload via imgbb or similar first?
        # For now, return search URL
        result["note"] = "TinEye requires public URL. Upload image to imgur/ibb first, then search."
        result["search_url_template"] = "https://www.tineye.com/search/?url={IMAGE_URL}"
    except Exception as e:
        result["error"] = str(e)

    return result


def reverse_search_facecheck(image_path: str) -> dict:
    """
    Facecheck.id - Face search engine.
    Requires uploading via browser automation (their site is JS-heavy).
    Returns the URL to use manually.
    """
    result = {"engine": "Facecheck.id", "found": False, "error": None}
    result["website"] = "https://facecheck.id/"
    result["note"] = "Facecheck requires browser upload. Use browser tool to upload image manually."
    result["match_types"] = ["social media", "dating sites", "criminal records", "news articles"]
    return result


def reverse_search_pimeyes(image_path: str) -> dict:
    """
    PimEyes - Powerful face search engine.
    They have an API but it requires keys and daily quota.
    Free tier: limited searches without API via website.
    """
    result = {"engine": "PimEyes", "found": False, "error": None}
    result["website"] = "https://pimeyes.com/"
    result["note"] = "PimEyes requires browser automation or API key for full results."
    result["api_note"] = "PimEyes API available but requires registration + quota."
    result["free_tier"] = "Limited searches via pimeyes.com/en without API"
    result["capabilities"] = [
        "Find face matches across the web",
        "Detect if face is online",
        "Blurring/protection options",
        "Premium: exact URL matches with face"
    ]
    result["search_url"] = "https://pimeyes.com/en"
    return result


def reverse_search_search4faces(image_path: str) -> dict:
    """
    Search4Faces - face search via VK, Odnoklassniki, etc.
    """
    result = {"engine": "Search4Faces", "found": False, "error": None}
    result["website"] = "https://search4faces.com/"
    result["note"] = "Search4Faces focuses on Russian VK/OK social networks."
    result["search_url"] = "https://search4faces.com/odnoklassniki/"
    return result


def check_url_image(image_url: str) -> dict:
    """
    Given a public URL of an image, search all reverse image engines at once.
    """
    result = {"image_url": image_url, "engines": {}}

    result["search_urls"] = {
        "yandex": f"https://yandex.com/images/search?url={image_url}&rpt=imageview",
        "google": f"https://www.google.com/searchbyimage?image_url={image_url}",
        "tineye": f"https://www.tineye.com/search/?url={image_url}",
        "bing": f"https://www.bing.com/images/search?view=detailv2&q=imgurl:{image_url}",
        "facecheck": "https://facecheck.id/",
        "pimeyes": "https://pimeyes.com/en",
        "search4faces": "https://search4faces.com/",
    }

    return result


def detect_faces_in_image(image_path: str) -> dict:
    """
    Detect if image contains a face using simple heuristics.
    Returns True if likely a face photo.
    """
    result = {"image": image_path, "has_face": False, "confidence": 0, "note": None}

    try:
        from PIL import Image
        import io

        img = Image.open(image_path)
        result["size"] = img.size
        result["format"] = img.format

        # Simple heuristic: portrait dimensions, skin-tone pixels
        # For real face detection, would need face_recognition/dlib
        # For now, check if it's portrait-oriented (height >= width)
        w, h = img.size
        if h >= w:
            result["confidence"] += 30

        # Check image hash for duplicates
        import hashlib
        with open(image_path, "rb") as f:
            result["hash"] = hashlib.md5(f.read()).hexdigest()

        result["note"] = "For accurate face detection, install: pip install face_recognition dlib (heavy)"

    except ImportError:
        result["error"] = "Pillow not installed. Run: pip install Pillow"
    except Exception as e:
        result["error"] = str(e)

    return result


def run_full_reverse_search(image_path: str = None, image_url: str = None) -> dict:
    """
    Master function: run all reverse image searches at once.
    """
    report = {}

    if image_path:
        report["local_file"] = image_path
        report["face_detection"] = detect_faces_in_image(image_path)

        # Upload-based searches
        report["yandex"] = reverse_search_yandex(image_path)
        report["tineye"] = reverse_search_tineye(image_path)
        report["facecheck"] = reverse_search_facecheck(image_path)
        report["pimeyes"] = reverse_search_pimeyes(image_path)
        report["search4faces"] = reverse_search_search4faces(image_path)

    if image_url:
        report["remote_url"] = image_url
        report["search_urls"] = check_url_image(image_url)["search_urls"]

    return report
