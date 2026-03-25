COLOR_MAP = {
    "red": (255, 0, 0),
    "green": (0, 255, 0),
    "blue": (0, 0, 255),
    "white": (255, 255, 255),
    "yellow": (255, 255, 0),
    "cyan": (0, 255, 255),
    "magenta": (255, 0, 255),
    "purple": (128, 0, 128),
    "pink": (255, 105, 180),
    "orange": (255, 165, 0),
    "lime": (50, 205, 50),
    "sky_blue": (135, 206, 235),
    "gold": (255, 215, 0),
    "teal": (0, 128, 128),
    "navy": (0, 0, 128),
    "brown": (139, 69, 19),
    "gray": (128, 128, 128),
    "black": (0, 0, 0),
    "violet": (238, 130, 238),
    "indigo": (75, 0, 130),
}

ALLOWED_LED_COLORS = list(COLOR_MAP.keys()) + ["off", "random"]
