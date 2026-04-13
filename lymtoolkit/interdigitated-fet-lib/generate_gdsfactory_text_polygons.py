import json
import sys


def main():
    if len(sys.argv) != 4:
        raise SystemExit("usage: generate_gdsfactory_text_polygons.py <text> <size_um> <justify>")

    text = sys.argv[1]
    size_um = float(sys.argv[2])
    justify = sys.argv[3]

    import gdsfactory as gf

    component = gf.components.text(
        text=text,
        size=size_um,
        justify=justify,
        layer=(1, 0),
    )
    bbox = component.bbox
    polygons = []
    for polygon in component.get_polygons():
        polygons.append([[float(x), float(y)] for x, y in polygon])

    payload = {
        "bbox": [[float(bbox[0][0]), float(bbox[0][1])], [float(bbox[1][0]), float(bbox[1][1])]],
        "polygons": polygons,
    }
    sys.stdout.write(json.dumps(payload))


if __name__ == "__main__":
    main()
