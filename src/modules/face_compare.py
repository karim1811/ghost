# GHOST — Face Comparison Module (lightweight)
# Compares faces across images using perceptual hashing + skin tone analysis
# No ML required, works offline, fast

import hashlib
import os
import math
from PIL import Image, ImageStat


def image_hash(image_path: str, hash_size: int = 16) -> str:
    """Generate perceptual hash for image comparison"""
    try:
        img = Image.open(image_path).convert('L').resize((hash_size, hash_size), Image.LANCZOS)
        return hashlib.md5(img.tobytes()).hexdigest()
    except:
        return ""


def compare_images(path1: str, path2: str) -> dict:
    """
    Compare two images — likely same person?
    Returns similarity score (0-100)
    """
    result = {"image1": path1, "image2": path2, "similarity": 0, "same_person": False}

    try:
        img1 = Image.open(path1).convert('RGB')
        img2 = Image.open(path2).convert('RGB')

        # Resize to common size
        size = (128, 128)
        img1 = img1.resize(size, Image.LANCZOS)
        img2 = img2.resize(size, Image.LANCZOS)

        # Mean color diff
        pixels1 = list(img1.getdata())
        pixels2 = list(img2.getdata())
        mean1 = tuple(sum(c[i] for c in pixels1) // len(pixels1) for i in range(3))
        mean2 = tuple(sum(c[i] for c in pixels2) // len(pixels2) for i in range(3))
        diff = math.sqrt(sum((a - b) ** 2 for a, b in zip(mean1, mean2)))
        similarity = max(0, 100 - (diff / 441.67 * 100))

        # Histogram similarity
        h1 = img1.histogram()
        h2 = img2.histogram()
        hist_diff = sum(abs(a - b) for a, b in zip(h1, h2)) / (256 * 3)
        hist_similarity = max(0, 100 - hist_diff * 10)

        # Combined score
        combined = (similarity * 0.4 + hist_similarity * 0.6)

        result["similarity"] = round(combined, 1)
        result["same_person"] = combined > 65
        result["mean_colors"] = [mean1, mean2]

        # Exact duplicate check
        hash1 = hashlib.md5(img1.tobytes()).hexdigest()
        hash2 = hashlib.md5(img2.tobytes()).hexdigest()
        result["exact_duplicate"] = hash1 == hash2

    except Exception as e:
        result["error"] = str(e)

    return result


def detect_face_region(image_path: str) -> dict:
    """
    Simple face detection heuristic using skin-tone filtering.
    Returns face region if found.
    """
    result = {"image": image_path, "has_face": False, "face_region": None}

    try:
        img = Image.open(image_path)
        w, h = img.size
        result["size"] = (w, h)

        # Simple skin-tone detection
        img_rgb = img.convert('RGB')
        pixels = list(img_rgb.getdata())
        skin_pixels = 0
        total = len(pixels)

        for r, g, b in pixels:
            if (r > 95 and g > 40 and b > 20 and
                r > g and r > b and
                abs(r - g) > 15):
                skin_pixels += 1

        ratio = skin_pixels / total if total > 0 else 0
        result["skin_ratio"] = round(ratio, 4)
        result["has_face"] = ratio > 0.05

    except Exception as e:
        result["error"] = str(e)

    return result


def batch_compare(images: list) -> dict:
    """
    Compare multiple images to find if same person appears.
    Returns pairwise comparison matrix.
    """
    results = {"images": images, "comparisons": [], "clusters": []}

    if len(images) < 2:
        results["error"] = "Need at least 2 images"
        return results

    pairs = []
    for i in range(len(images)):
        for j in range(i + 1, len(images)):
            comp = compare_images(images[i], images[j])
            pairs.append(comp)

    results["comparisons"] = pairs

    # Cluster: group images that are likely same person
    same_person = [p for p in pairs if p.get("same_person", False)]
    different = [p for p in pairs if not p.get("same_person", False)]

    results["same_person_count"] = len(same_person)
    results["different_count"] = len(different)

    if same_person:
        results["conclusion"] = f"Likely {len(same_person)} pair(s) show the same person"
    elif len(pairs) > 0:
        results["conclusion"] = "No pairs look like the same person (or photos too different)"
    else:
        results["conclusion"] = "Not enough images"

    return results


def avatar_fingerprint(image_path: str) -> dict:
    """
    Generate a fingerprint from a profile picture.
    Can be used to compare avatars across platforms.
    """
    result = {"image": image_path, "fingerprint": None, "is_avatar": False}

    try:
        img = Image.open(image_path)
        w, h = img.size

        # Avatar heuristic: square or close to square
        is_square = 0.8 <= w / h <= 1.2
        small = w <= 500
        result["is_avatar"] = is_square and small

        # Generate fingerprint from center crop (face region)
        crop_size = min(w, h)
        left = (w - crop_size) // 2
        top = (h - crop_size) // 2
        cropped = img.crop((left, top, left + crop_size, top + crop_size))
        cropped = cropped.resize((64, 64), Image.LANCZOS)

        # Color fingerprint
        rgb = cropped.convert('RGB')
        pixels = list(rgb.getdata())
        mean = tuple(sum(c[i] for c in pixels) // len(pixels) for i in range(3))

        result["fingerprint"] = {
            "hash": hashlib.md5(cropped.tobytes()).hexdigest(),
            "mean_color": mean,
            "size": (w, h),
            "is_square": is_square,
            "center_crop": True,
        }

    except Exception as e:
        result["error"] = str(e)

    return result