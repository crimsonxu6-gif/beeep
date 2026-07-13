from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from common import EVAL_ROOT, IMAGES_ROOT, MANIFEST_ROOT, read_jsonl, write_jsonl


@dataclass(frozen=True)
class TransformRecipe:
    image_id: str
    parent_id: str
    operation: str
    scenario: str
    expected_person_present: bool


RECIPES = [
    TransformRecipe("tf_dark_front", "public_front_face", "dark", "weak_light", True),
    TransformRecipe(
        "tf_overexposed_profile",
        "public_side_profile",
        "overexposed",
        "overexposed",
        True,
    ),
    TransformRecipe(
        "tf_gaussian_mask", "public_mask", "gaussian_blur", "blurred_face", True
    ),
    TransformRecipe(
        "tf_motion_group", "ai_group_edge", "motion_blur", "motion_blur_group", True
    ),
    TransformRecipe(
        "tf_jpeg_hat", "public_hat", "jpeg_compression", "jpeg_artifacts", True
    ),
    TransformRecipe(
        "tf_occluded_sunglasses",
        "public_sunglasses",
        "partial_occlusion",
        "face_occluded",
        True,
    ),
    TransformRecipe(
        "tf_shrunk_full_body",
        "public_full_body",
        "subject_shrink",
        "person_very_small",
        True,
    ),
    TransformRecipe(
        "tf_mirror_side",
        "ai_side_profile",
        "horizontal_mirror",
        "side_profile_mirrored",
        True,
    ),
    TransformRecipe(
        "tf_rotate_down", "ai_looking_down", "rotate", "rotated_looking_down", True
    ),
    TransformRecipe(
        "tf_crop_left_group", "ai_group_edge", "crop_left", "person_at_edge", True
    ),
    TransformRecipe(
        "tf_crop_right_back", "ai_back_view", "crop_right", "back_view_cropped", True
    ),
    TransformRecipe(
        "tf_crop_top_mask", "ai_mask_hat", "crop_top", "hat_top_cropped", True
    ),
    TransformRecipe(
        "tf_crop_bottom_full",
        "public_full_body",
        "crop_bottom",
        "full_body_bottom_cropped",
        True,
    ),
    TransformRecipe(
        "tf_dark_empty", "public_empty_room", "dark", "empty_room_dark", False
    ),
    TransformRecipe(
        "tf_blur_empty",
        "public_empty_room",
        "gaussian_blur",
        "empty_room_blurred",
        False,
    ),
    TransformRecipe(
        "tf_mirror_mannequin",
        "ai_mannequin_poster",
        "horizontal_mirror",
        "negative_mannequin_poster_mirrored",
        False,
    ),
]


def _catalog() -> dict[str, dict]:
    rows = read_jsonl(MANIFEST_ROOT / "public_sources.jsonl") + read_jsonl(
        MANIFEST_ROOT / "ai_sources.jsonl"
    )
    return {row["image_id"]: row for row in rows}


def _image_path(record: dict) -> Path:
    return EVAL_ROOT / record["image_path"]


def _transform(image: np.ndarray, operation: str) -> np.ndarray:
    height, width = image.shape[:2]
    if operation == "dark":
        return np.clip(image.astype(np.float32) * 0.28, 0, 255).astype(np.uint8)
    if operation == "overexposed":
        return cv2.convertScaleAbs(image, alpha=1.6, beta=65)
    if operation == "gaussian_blur":
        return cv2.GaussianBlur(image, (19, 19), 5)
    if operation == "motion_blur":
        kernel = np.zeros((17, 17), dtype=np.float32)
        kernel[8, :] = 1 / 17
        return cv2.filter2D(image, -1, kernel)
    if operation == "jpeg_compression":
        encoded = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 12])[1]
        return cv2.imdecode(encoded, cv2.IMREAD_COLOR)
    if operation == "partial_occlusion":
        result = image.copy()
        cv2.rectangle(
            result,
            (int(width * 0.25), int(height * 0.28)),
            (int(width * 0.72), int(height * 0.52)),
            (38, 38, 38),
            thickness=-1,
        )
        return result
    if operation == "subject_shrink":
        scaled = cv2.resize(image, (int(width * 0.42), int(height * 0.42)))
        canvas = cv2.GaussianBlur(image, (31, 31), 12)
        y = (height - scaled.shape[0]) // 2
        x = (width - scaled.shape[1]) // 2
        canvas[y : y + scaled.shape[0], x : x + scaled.shape[1]] = scaled
        return canvas
    if operation == "horizontal_mirror":
        return cv2.flip(image, 1)
    if operation == "rotate":
        matrix = cv2.getRotationMatrix2D((width / 2, height / 2), 12, 1)
        return cv2.warpAffine(
            image, matrix, (width, height), borderMode=cv2.BORDER_REFLECT
        )

    fractions = {
        "crop_left": (0.18, 0, 1, 1),
        "crop_right": (0, 0, 0.82, 1),
        "crop_top": (0, 0.18, 1, 1),
        "crop_bottom": (0, 0, 1, 0.82),
    }
    if operation in fractions:
        x1, y1, x2, y2 = fractions[operation]
        crop = image[
            int(y1 * height) : int(y2 * height), int(x1 * width) : int(x2 * width)
        ]
        return cv2.resize(crop, (width, height), interpolation=cv2.INTER_CUBIC)
    raise ValueError(f"unsupported operation: {operation}")


def transform(*, force: bool = False) -> list[dict]:
    catalog = _catalog()
    records = []
    destination_root = IMAGES_ROOT / "transformed"
    destination_root.mkdir(parents=True, exist_ok=True)
    for recipe in RECIPES:
        parent = catalog.get(recipe.parent_id)
        if parent is None:
            raise FileNotFoundError(f"missing source metadata: {recipe.parent_id}")
        source = _image_path(parent)
        if not source.exists():
            raise FileNotFoundError(f"missing source image: {source}")
        destination = destination_root / f"{recipe.image_id}.jpg"
        if force or not destination.exists():
            image = cv2.imread(str(source), cv2.IMREAD_COLOR)
            if image is None:
                raise ValueError(f"cannot decode image: {source}")
            height, width = image.shape[:2]
            scale = min(1.0, 1280 / max(width, height))
            if scale < 1:
                image = cv2.resize(image, (int(width * scale), int(height * scale)))
            cv2.imwrite(
                str(destination),
                _transform(image, recipe.operation),
                [cv2.IMWRITE_JPEG_QUALITY, 86],
            )
        records.append(
            {
                "image_id": recipe.image_id,
                "image_path": destination.relative_to(EVAL_ROOT).as_posix(),
                "source_kind": "transformed",
                "parent_id": recipe.parent_id,
                "parent_source_kind": parent["source_kind"],
                "operation": recipe.operation,
                "scenario": recipe.scenario,
                "expected_person_present": recipe.expected_person_present,
            }
        )
    write_jsonl(MANIFEST_ROOT / "transformed_sources.jsonl", records)
    return records


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate deterministic camera-quality variants."
    )
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    records = transform(force=args.force)
    print(f"transformed={len(records)}")


if __name__ == "__main__":
    main()
