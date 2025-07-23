import json
from typing import List, Dict

from flask import Flask


def discover_endpoints(app: Flask) -> List[Dict[str, object]]:
    output = []
    for rule in app.url_map.iter_rules():
        if rule.endpoint == "static":
            continue
        output.append(
            {
                "path": str(rule),
                "methods": list(rule.methods - {"HEAD", "OPTIONS"}),
            }
        )
    return output


def main(app: Flask):
    endpoints = discover_endpoints(app)
    with open("tests/tmp/endpoints.json", "w") as f:
        json.dump(endpoints, f, indent=2)


if __name__ == "__main__":
    from tests.conftest import flask_app

    main(flask_app)
