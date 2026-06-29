# GHOST — Face Recognition Module (FaceOnLive + Azure Face API)
# Recherche faciale, comparaison, détection de visages

import os
import json
import base64
import httpx
from pathlib import Path
from typing import Optional

# ── Config ──────────────────────────────────────────────
_FACEONLIVE_KEY_NAME = "FACEONLIVE_API_KEY"
_AZURE_FACE_KEY_NAME = "AZURE_FACE_API_KEY"
_AZURE_FACE_ENDPOINT_NAME = "AZURE_FACE_ENDPOINT"

FACEONLIVE_API_KEY = os.getenv(_FACEONLIVE_KEY_NAME, "")
AZURE_FACE_API_KEY = os.getenv(_AZURE_FACE_KEY_NAME, "")
AZURE_FACE_ENDPOINT = os.getenv(_AZURE_FACE_ENDPOINT_NAME, "https://api.cognitive.microsoft.com")

# ── FaceOnLive ──────────────────────────────────────────

def faceonlive_search(image_path: str = None, image_url: str = None) -> dict:
    """
    FaceOnLive reverse face search (PimEyes alternative).
    Finds where a face appears online.
    
    Requires FaceOnLive API key from https://faceonlive.com
    """
    result = {
        "source": "FaceOnLive",
        "found": False,
        "matches": [],
        "error": None,
    }

    if not FACEONLIVE_API_KEY:
        result["error"] = "API key required (FACEONLIVE_API_KEY)"
        return result

    try:
        url = "https://api.faceonlive.com/face_search/v1/search"
        headers = {"Authorization": f"Bearer {FACEONLIVE_API_KEY}"}

        if image_path and Path(image_path).exists():
            with open(image_path, "rb") as f:
                files = {"image": (Path(image_path).name, f, "image/jpeg")}
                r = httpx.post(url, headers=headers, files=files, timeout=60)
        elif image_url:
            data = {"url": image_url}
            r = httpx.post(url, headers=headers, json=data, timeout=60)
        else:
            result["error"] = "No image provided"
            return result

        if r.status_code == 200:
            data = r.json()
            result["found"] = True
            result["matches"] = data.get("matches", data.get("results", []))
        else:
            result["error"] = f"HTTP {r.status_code}: {r.text[:200]}"

    except Exception as e:
        result["error"] = str(e)

    return result


def faceonlive_liveness(image_path: str = None, image_url: str = None) -> dict:
    """
    FaceOnLive liveness detection (anti-spoofing).
    Checks if a face is real (not a photo of a photo, mask, etc.)
    """
    result = {
        "source": "FaceOnLive Liveness",
        "is_live": None,
        "confidence": 0,
        "error": None,
    }

    if not FACEONLIVE_API_KEY:
        result["error"] = "API key required"
        return result

    try:
        url = "https://api.faceonlive.com/liveness/v1/check"
        headers = {"Authorization": f"Bearer {FACEONLIVE_API_KEY}"}

        if image_path and Path(image_path).exists():
            with open(image_path, "rb") as f:
                files = {"image": (Path(image_path).name, f, "image/jpeg")}
                r = httpx.post(url, headers=headers, files=files, timeout=30)
        elif image_url:
            data = {"url": image_url}
            r = httpx.post(url, headers=headers, json=data, timeout=30)
        else:
            result["error"] = "No image provided"
            return result

        if r.status_code == 200:
            data = r.json()
            result["is_live"] = data.get("is_live", data.get("liveness", False))
            result["confidence"] = data.get("confidence", 0)
        else:
            result["error"] = f"HTTP {r.status_code}"

    except Exception as e:
        result["error"] = str(e)

    return result


# ── Azure Face API ──────────────────────────────────────

def azure_detect_faces(image_path: str = None, image_url: str = None) -> dict:
    """
    Azure Face API — face detection with attributes.
    Free tier: 20 transactions/min, 30k/month.
    
    Returns: age, gender, emotion, glasses, facial hair, etc.
    """
    result = {
        "source": "Azure Face API",
        "found": False,
        "faces": [],
        "error": None,
    }

    if not AZURE_FACE_API_KEY:
        result["error"] = "API key required (AZURE_FACE_API_KEY)"
        return result

    try:
        endpoint = AZURE_FACE_ENDPOINT.rstrip("/")
        url = f"{endpoint}/face/v1.0/detect"
        headers = {
            "Ocp-Apim-Subscription-Key": AZURE_FACE_API_KEY,
            "Content-Type": "application/octet-stream",
        }
        params = {
            "returnFaceId": "true",
            "returnFaceAttributes": "age,gender,headPose,smile,facialHair,glasses,emotion,makeup,hair,accessories,blur,exposure,noise",
        }

        if image_path and Path(image_path).exists():
            with open(image_path, "rb") as f:
                image_data = f.read()
            r = httpx.post(url, headers=headers, params=params, content=image_data, timeout=30)
        elif image_url:
            headers["Content-Type"] = "application/json"
            r = httpx.post(url, headers=headers, params=params, json={"url": image_url}, timeout=30)
        else:
            result["error"] = "No image provided"
            return result

        if r.status_code == 200:
            faces = r.json()
            if faces:
                result["found"] = True
                result["faces"] = faces
        else:
            result["error"] = f"HTTP {r.status_code}: {r.text[:200]}"

    except Exception as e:
        result["error"] = str(e)

    return result


def azure_verify_faces(image_path1: str, image_path2: str) -> dict:
    """
    Azure Face API — verify if two faces are the same person.
    Free tier available.
    """
    result = {
        "source": "Azure Face Verify",
        "same_person": False,
        "confidence": 0,
        "error": None,
    }

    if not AZURE_FACE_API_KEY:
        result["error"] = "API key required"
        return result

    try:
        endpoint = AZURE_FACE_ENDPOINT.rstrip("/")

        # Step 1: Detect faces in both images
        detect_url = f"{endpoint}/face/v1.0/detect"
        headers = {"Ocp-Apim-Subscription-Key": AZURE_FACE_API_KEY}

        face_ids = []
        for img_path in [image_path1, image_path2]:
            if not Path(img_path).exists():
                result["error"] = f"File not found: {img_path}"
                return result
            with open(img_path, "rb") as f:
                r = httpx.post(detect_url, headers=headers, content=f.read(), timeout=30,
                             params={"returnFaceId": "true"})
            if r.status_code == 200 and r.json():
                face_ids.append(r.json()[0]["faceId"])
            else:
                result["error"] = f"No face detected in {img_path}"
                return result

        # Step 2: Verify
        verify_url = f"{endpoint}/face/v1.0/verify"
        r = httpx.post(verify_url, headers=headers, json={
            "faceId1": face_ids[0],
            "faceId2": face_ids[1],
        }, timeout=30)

        if r.status_code == 200:
            data = r.json()
            result["same_person"] = data.get("isIdentical", False)
            result["confidence"] = data.get("confidence", 0)
        else:
            result["error"] = f"HTTP {r.status_code}"

    except Exception as e:
        result["error"] = str(e)

    return result


def azure_find_similar(face_image_path: str, face_list_id: str = None) -> dict:
    """
    Azure Face API — find similar faces in a stored list.
    Useful for building a database of known faces.
    """
    result = {
        "source": "Azure Find Similar",
        "found": False,
        "matches": [],
        "error": None,
    }

    if not AZURE_FACE_API_KEY:
        result["error"] = "API key required"
        return result

    try:
        endpoint = AZURE_FACE_ENDPOINT.rstrip("/")

        # Detect face
        detect_url = f"{endpoint}/face/v1.0/detect"
        headers = {"Ocp-Apim-Subscription-Key": AZURE_FACE_API_KEY}
        with open(face_image_path, "rb") as f:
            r = httpx.post(detect_url, headers=headers, content=f.read(), timeout=30,
                         params={"returnFaceId": "true"})
        if r.status_code != 200 or not r.json():
            result["error"] = "No face detected"
            return result

        face_id = r.json()[0]["faceId"]

        # Find similar
        if face_list_id:
            url = f"{endpoint}/face/v1.0/findsimilars"
            r = httpx.post(url, headers=headers, json={
                "faceId": face_id,
                "faceListId": face_list_id,
                "maxNumOfCandidatesReturned": 10,
            }, timeout=30)

            if r.status_code == 200:
                matches = r.json()
                if matches:
                    result["found"] = True
                    result["matches"] = matches

    except Exception as e:
        result["error"] = str(e)

    return result


# ── Combined Face Analysis ──────────────────────────────

def full_face_analysis(image_path: str = None, image_url: str = None) -> dict:
    """
    Complete face analysis using all available services.
    Combines FaceOnLive search + Azure detection.
    """
    result = {
        "image": image_path or image_url,
        "faceonlive": None,
        "azure": None,
        "liveness": None,
        "summary": {},
    }

    # FaceOnLive search
    if FACEONLIVE_API_KEY:
        result["faceonlive"] = faceonlive_search(image_path, image_url)
        result["liveness"] = faceonlive_liveness(image_path, image_url)

    # Azure Face API
    if AZURE_FACE_API_KEY:
        result["azure"] = azure_detect_faces(image_path, image_url)

    # Build summary
    summary = {}

    if result["azure"] and result["azure"].get("found"):
        face = result["azure"]["faces"][0]
        attrs = face.get("faceAttributes", {})
        summary["age"] = attrs.get("age")
        summary["gender"] = attrs.get("gender")
        summary["emotion"] = max(attrs.get("emotion", {}).items(), key=lambda x: x[1])[0] if attrs.get("emotion") else None
        summary["glasses"] = attrs.get("glasses")
        summary["facial_hair"] = attrs.get("facialHair", {}).get("moustache", 0) > 0.5
        summary["smile"] = attrs.get("smile", 0) > 0.5

    if result["liveness"]:
        summary["is_live"] = result["liveness"].get("is_live")
        summary["liveness_confidence"] = result["liveness"].get("confidence")

    if result["faceonlive"] and result["faceonlive"].get("found"):
        summary["online_matches"] = len(result["faceonlive"].get("matches", []))

    result["summary"] = summary
    return result
