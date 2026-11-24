"""Style presets for photos and videos. Every preset only applies global tone/colour
adjustments: nothing here adds, removes or reshapes objects in the property."""

STYLES = ["natural", "real_estate", "luxury", "cinematic", "night"]

PHOTO_DEFAULTS = {
    "exposure": 0.0, "contrast": 0.0, "highlights": 0.0, "shadows": 0.0,
    "saturation": 0.0, "vibrance": 0.0, "warmth": 0.0, "tint": 0.0,
    "clarity": 0.0, "sharpen": 0.0, "denoise": 0.0, "vignette": 0.0,
    "teal_orange": 0.0, "golden": 0.0,
    "auto_wb": False, "auto_levels": False,
    "rotate": 0.0, "perspective_v": 0.0,
}

PHOTO_STYLES = {
    "natural": {"auto_wb": True, "auto_levels": True, "contrast": 0.05, "vibrance": 0.12,
                "clarity": 0.1, "sharpen": 0.25},
    "real_estate": {"auto_wb": True, "auto_levels": True, "exposure": 0.1, "shadows": 0.35,
                    "highlights": -0.4, "contrast": 0.08, "vibrance": 0.18, "saturation": 0.03,
                    "clarity": 0.15, "sharpen": 0.25},
    "luxury": {"auto_levels": True, "shadows": 0.2, "highlights": -0.3, "contrast": 0.18,
               "saturation": -0.05, "warmth": 0.2, "golden": 0.5, "clarity": 0.2,
               "sharpen": 0.3, "vignette": 0.3},
    "cinematic": {"auto_levels": True, "contrast": 0.22, "saturation": -0.12, "teal_orange": 0.6,
                  "highlights": -0.3, "shadows": 0.1, "clarity": 0.15, "sharpen": 0.2,
                  "vignette": 0.4},
    "night": {"auto_wb": True, "exposure": 0.35, "shadows": 0.5, "highlights": -0.4,
              "denoise": 0.6, "vibrance": 0.15, "contrast": 0.06, "clarity": 0.1, "sharpen": 0.15},
}

VIDEO_DEFAULTS = {
    "brightness": 0.0, "contrast": 1.0, "saturation": 1.0, "gamma": 1.0,
    "warmth": 0.0, "teal_orange": 0.0, "vignette": 0.0, "sharpen": 0.0,
    "denoise": 0.0, "letterbox": False,
}

VIDEO_STYLES = {
    "natural": {"contrast": 1.04, "saturation": 1.06, "sharpen": 0.2},
    "real_estate": {"brightness": 0.02, "contrast": 1.07, "saturation": 1.15, "gamma": 1.06,
                    "sharpen": 0.35},
    "luxury": {"contrast": 1.12, "saturation": 1.02, "warmth": 0.5, "vignette": 0.4, "sharpen": 0.3},
    "cinematic": {"contrast": 1.15, "saturation": 0.92, "teal_orange": 0.7, "vignette": 0.5,
                  "letterbox": True, "sharpen": 0.2},
    "night": {"brightness": 0.05, "gamma": 1.3, "contrast": 1.05, "saturation": 1.1,
              "denoise": 0.6, "sharpen": 0.15},
}


def photo_style(name: str) -> dict:
    p = dict(PHOTO_DEFAULTS)
    p.update(PHOTO_STYLES.get(name, {}))
    return p


def video_style(name: str) -> dict:
    p = dict(VIDEO_DEFAULTS)
    p.update(VIDEO_STYLES.get(name, {}))
    return p
