#!/usr/bin/env python3
"""Run the Christmakah Secret Santa draw and bake it into index.html.

Prints only validation results -- never the pairings -- so whoever runs it
(who is also in the draw) stays in the dark. Re-run to reshuffle; everyone's
old assignment is replaced.
"""
import base64
import json
import re
import secrets
from pathlib import Path

NAMES = ["John", "Natalie", "Marina", "Jeanne", "Cris", "Lauren", "Elisa", "Erynne", "Devon"]

# giver -> the only people they may be assigned
ALLOWED = {
    "Devon": {"Erynne", "Cris", "Jeanne", "Elisa"},
}

PAGE = Path(__file__).with_name("index.html")
rng = secrets.SystemRandom()


def valid(assign):
    if any(g == r for g, r in assign.items()):
        return False
    return all(assign[g] in ok for g, ok in ALLOWED.items())


def draw():
    # Rejection sampling: uniformly random among all valid draws.
    while True:
        recipients = NAMES[:]
        rng.shuffle(recipients)
        assign = dict(zip(NAMES, recipients))
        if valid(assign):
            return assign


def encode(giver, recipient, salt):
    key = (salt + giver).encode()
    data = recipient.encode()
    return base64.b64encode(bytes(b ^ key[i % len(key)] for i, b in enumerate(data))).decode()


def decode(giver, blob, salt):
    key = (salt + giver).encode()
    data = base64.b64decode(blob)
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data)).decode()


def main():
    assign = draw()
    salt = secrets.token_hex(6)
    blob = {"salt": salt, "map": {g: encode(g, assign[g], salt) for g in NAMES}}

    html = PAGE.read_text()
    block = "// @@DRAW-START\nconst DRAW = " + json.dumps(blob, indent=2) + ";\n// @@DRAW-END"
    html, n = re.subn(r"// @@DRAW-START.*?// @@DRAW-END", lambda _: block, html, flags=re.S)
    assert n == 1, "DRAW markers not found in index.html"
    PAGE.write_text(html)

    # Verify what was written, without revealing it.
    decoded = {g: decode(g, blob["map"][g], salt) for g in NAMES}
    checks = {
        "everyone gives exactly once": sorted(decoded) == sorted(NAMES),
        "everyone receives exactly once": sorted(decoded.values()) == sorted(NAMES),
        "nobody drew themselves": all(g != r for g, r in decoded.items()),
        "Devon -> Erynne/Cris/Jeanne/Elisa": decoded["Devon"] in ALLOWED["Devon"],
    }
    for label, ok in checks.items():
        print(("PASS  " if ok else "FAIL  ") + label)
    if not all(checks.values()):
        raise SystemExit("Draw failed validation")
    print(f"Draw written to {PAGE.name} ({len(NAMES)} people). Pairings not shown.")


if __name__ == "__main__":
    main()
