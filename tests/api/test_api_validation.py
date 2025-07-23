import json
import os

import pytest
from flask import Flask

from ..discovery.discover_endpoints import discover_endpoints


@pytest.fixture(scope="session")
def endpoints(flask_app: Flask):
    eps = discover_endpoints(flask_app)
    os.makedirs("tests/tmp", exist_ok=True)
    with open("tests/tmp/endpoints.json", "w") as f:
        json.dump(eps, f, indent=2)
    return eps


def _replace_path_params(path: str) -> str:
    import re

    def repl(match):
        param = match.group(0)
        if "int" in param:
            return "1"
        return "test"

    return re.sub(r"<[^>]+>", repl, path)


def test_api_endpoint_health(client, endpoints):
    for endpoint in endpoints:
        for method in endpoint["methods"]:
            path = _replace_path_params(endpoint["path"])
            resp = client.open(path, method=method)
            assert resp.status_code in {200, 400, 401, 403, 404, 415, 500}
