from __future__ import annotations

import argparse
import json
import time
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from PIL import Image, ImageOps

from common import IMAGES_ROOT, MANIFEST_ROOT, strip_html, write_jsonl

API_URL = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = "BeeepEvaluation/0.1 (https://github.com/crimsonxu6-gif/beeep; offline CV evaluation)"
ALLOWED_LICENSE_PREFIXES = ("CC0", "CC BY", "Public domain", "PDM")

PUBLIC_SOURCES = [
    ("public_front_face", "File:Fatih Husni.jpg", "front_face", True),
    (
        "public_side_profile",
        "File:Profile Photographic Portrait of Blonde Young Woman.jpg",
        "side_profile",
        True,
    ),
    ("public_back_view", "File:ATEKER-81.jpg", "back_view", True),
    ("public_looking_down", "File:Meet up Day 2 3506.jpg", "looking_down", True),
    (
        "public_hat",
        "File:Two hikers affectionately posing in front of the Gamájåhkå rapids in Kvikkjokk, Sweden (DSCF2456).jpg",
        "hat",
        True,
    ),
    ("public_sunglasses", "File:Zenofilius lovelace.jpeg", "sunglasses", True),
    (
        "public_group",
        "File:Wikimedia Summit 2019, Berlin (P1080136).jpg",
        "multiple_people",
        True,
    ),
    ("public_empty_room", "File:Chaillot - Grand Foyer.jpg", "empty_room", False),
    (
        "public_mask",
        "File:Nancy Pelosi at Prime Minister's official Residential Quarters (2).jpg",
        "mask",
        True,
    ),
    (
        "public_full_body",
        "File:GEN Duane H. Cassidy, full body portrait (uncovered).jpg",
        "full_body",
        True,
    ),
]


def _request(url: str, *, retries: int = 4) -> bytes:
    for attempt in range(retries):
        try:
            request = Request(
                url,
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": "application/json,image/jpeg,image/png,image/webp,*/*;q=0.5",
                    "Referer": "https://commons.wikimedia.org/",
                },
            )
            with urlopen(request, timeout=30) as response:
                return response.read()
        except HTTPError as exc:
            if exc.code not in {429, 500, 502, 503, 504} or attempt == retries - 1:
                raise
        except URLError:
            if attempt == retries - 1:
                raise
        time.sleep(5 * (attempt + 1))
    raise RuntimeError("unreachable")


def _metadata() -> dict[str, dict]:
    params = {
        "action": "query",
        "titles": "|".join(title for _, title, _, _ in PUBLIC_SOURCES),
        "prop": "imageinfo",
        "iiprop": "url|extmetadata|size",
        "iiurlwidth": "1400",
        "format": "json",
        "formatversion": "2",
    }
    payload = json.loads(_request(f"{API_URL}?{urlencode(params)}"))
    pages = payload.get("query", {}).get("pages", [])
    return {page["title"]: page for page in pages}


def _license(metadata: dict) -> tuple[str, str | None]:
    ext = metadata.get("extmetadata", {})
    short_name = ext.get("LicenseShortName", {}).get("value", "")
    license_url = ext.get("LicenseUrl", {}).get("value")
    if not short_name.startswith(ALLOWED_LICENSE_PREFIXES):
        raise ValueError(f"license is not allowed: {short_name or 'missing'}")
    return short_name, license_url


def _save_jpeg(data: bytes, destination: Path) -> None:
    with Image.open(BytesIO(data)) as source:
        image = ImageOps.exif_transpose(source).convert("RGB")
        image.thumbnail((1400, 1400), Image.Resampling.LANCZOS)
        destination.parent.mkdir(parents=True, exist_ok=True)
        image.save(destination, format="JPEG", quality=88, optimize=True)


def download(*, force: bool = False) -> list[dict]:
    pages = _metadata()
    downloaded_at = datetime.now(UTC).isoformat()
    records = []
    for image_id, title, scenario, expected in PUBLIC_SOURCES:
        page = pages.get(title)
        if not page or not page.get("imageinfo"):
            raise RuntimeError(f"Wikimedia Commons file is unavailable: {title}")
        info = page["imageinfo"][0]
        license_name, license_url = _license(info)
        ext = info.get("extmetadata", {})
        destination = IMAGES_ROOT / "source" / f"{image_id}.jpg"
        if force or not destination.exists():
            _save_jpeg(_request(info.get("thumburl") or info["url"]), destination)
            time.sleep(0.25)
        records.append(
            {
                "image_id": image_id,
                "image_path": destination.relative_to(IMAGES_ROOT.parent).as_posix(),
                "source_kind": "public_real",
                "source_url": info.get("descriptionurl"),
                "author": strip_html(ext.get("Artist", {}).get("value")),
                "license": license_name,
                "license_url": license_url,
                "downloaded_at": downloaded_at,
                "scenario": scenario,
                "expected_person_present": expected,
                "commons_title": title,
            }
        )
    write_jsonl(MANIFEST_ROOT / "public_sources.jsonl", records)
    return records


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download pinned, license-checked Commons images."
    )
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    records = download(force=args.force)
    print(f"downloaded_or_verified={len(records)}")


if __name__ == "__main__":
    main()
