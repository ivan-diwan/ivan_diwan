def make_geometry(x: int, y: int, width: int, height: int) -> dict:
    return {"x": int(x), "y": int(y), "width": int(width), "height": int(height)}


def normalize_geometry(data: dict) -> dict:
    return make_geometry(
        x=int(data["x"]),
        y=int(data["y"]),
        width=int(data["width"]),
        height=int(data["height"]),
    )
