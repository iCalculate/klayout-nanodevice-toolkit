import json
import site
import sys


def _ensure_user_site():
    candidates = []
    try:
        candidates.extend(site.getsitepackages())
    except Exception:
        pass
    try:
        candidates.append(site.getusersitepackages())
    except Exception:
        pass

    for path in candidates:
        if path and path not in sys.path:
            sys.path.append(path)


def _extract_polygons(component):
    if hasattr(component, "get_polygons_points"):
        polygons = component.get_polygons_points()
        if isinstance(polygons, dict):
            return list(polygons.values())
        return list(polygons)
    if hasattr(component, "get_polygons"):
        return list(component.get_polygons())
    raise RuntimeError("gdsfactory text component does not expose polygon extraction API")


def main():
    if len(sys.argv) != 4:
        raise SystemExit("usage: generate_gdsfactory_text_polygons.py <text> <size_um> <justify>")

    text = sys.argv[1]
    size_um = float(sys.argv[2])
    justify = sys.argv[3]

    _ensure_user_site()
    import gdsfactory as gf

    component = gf.components.text(
        text=text,
        size=size_um,
        justify=justify,
        layer=(1, 0),
    )
    bbox = component.bbox
    polygons = []
    for polygon in _extract_polygons(component):
        polygons.append([[float(x), float(y)] for x, y in polygon])

    payload = {
        "bbox": [[float(bbox[0][0]), float(bbox[0][1])], [float(bbox[1][0]), float(bbox[1][1])]],
        "polygons": polygons,
    }
    sys.stdout.write(json.dumps(payload))


if __name__ == "__main__":
    main()
