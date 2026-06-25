"""Find all active chromium browser revisions across patchright installations."""

import glob
import json
import os
from importlib.resources import files


def revs_from_dir(browsers_json_dir: str) -> list[str]:
    """Extract chromium revision numbers from a browsers.json directory."""
    bjson = os.path.join(browsers_json_dir, "package", "browsers.json")
    if not os.path.isfile(bjson):
        return []
    browsers = json.loads(open(bjson).read())
    return [
        b["revision"]
        for b in browsers["browsers"]
        if b["name"] in ("chromium", "chromium-headless-shell")
    ]


def main() -> None:
    all_revs: set[str] = set()

    # Project venv's patchright
    try:
        bjson = files("patchright.driver").joinpath("package/browsers.json")
        browsers = json.loads(bjson.read_text())
        all_revs.update(
            b["revision"]
            for b in browsers["browsers"]
            if b["name"] in ("chromium", "chromium-headless-shell")
        )
    except Exception:
        pass

    # Globally installed uv tools that use patchright
    tools_dir = os.path.expanduser("~/.local/share/uv/tools")
    if os.path.isdir(tools_dir):
        for tool in os.listdir(tools_dir):
            pattern = os.path.join(
                tools_dir, tool, "lib/python*/site-packages/patchright/driver"
            )
            for p in glob.glob(pattern):
                all_revs.update(revs_from_dir(p))

    # Output comma-separated, sorted revision numbers
    if all_revs:
        print(",".join(sorted(all_revs)))


if __name__ == "__main__":
    main()
