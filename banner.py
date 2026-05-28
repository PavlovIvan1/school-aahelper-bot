from pathlib import Path

import config

PREFERRED_BANNER_NAMES = (
    "поддержка_баннер.jpg",
    "banner.jpg",
)


def resolve_banner_path() -> Path | None:
    if not config.ASSETS_DIR.is_dir():
        return None

    for name in PREFERRED_BANNER_NAMES:
        path = config.ASSETS_DIR / name
        if path.is_file():
            return path

    for ext in ("*.jpg", "*.jpeg", "*.png", "*.webp"):
        matches = sorted(config.ASSETS_DIR.glob(ext))
        if matches:
            return matches[0]

    return None
