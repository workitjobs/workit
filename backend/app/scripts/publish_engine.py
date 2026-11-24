"""
Publish a Fill engine build for WorkIt Auto Apply to download (KAN-836, W7
of docs/desktop_application_auto_apply.md; app/services/engine_builds.py).

.github/workflows/publish-engine.yml runs `publish` on each merge to main
that moves the engine pointer or MIN_APP's file, with the key from its
secret (.github/CLAUDE.md, "Publish the Fill engine"). By hand:

  uv run python -m app.scripts.publish_engine make-key <private key file>
      A new Ed25519 engine key: the private key to that file (mode 600,
      never over an old one), and the public key printed, for Apply's
      `engine_download.PUBLIC_KEY`. Done once. Keep the file outside every
      checkout; whoever holds it can make every app run their code.

  uv run python -m app.scripts.publish_engine publish --key <file> [--min-app <version>] [--engine <dist/engine.js>] [--dry-run]
      Signs the engine bundle (the submodule's dist/engine.js by default),
      uploads it to the private `ApplyEngine` bucket as <sha256>.js and puts
      its line last in builds.json. Apps at --min-app (MIN_APP's file by
      default) or later get it from their next launch (within
      engine_builds.INDEX_TTL of the API reading it). A build that would
      break older apps gets a higher --min-app, so they keep the build
      before it. It refuses a key whose public half Apply doesn't hold:
      every app would refuse its build.

A real publish writes to the Storage of the Supabase project that
SUPABASE_URL names, as the import does to its database: the workflow or
the user runs it, never Claude. The `ApplyEngine` bucket is made once in
the Supabase dashboard (Storage, New bucket, Public off).
"""

import argparse
import base64
import datetime
import hashlib
import json
import os
import re
import sys
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from app.services.engine_builds import BUCKET, INDEX, version

ROOT = Path(__file__).resolve().parents[3]
ENGINE = ROOT / "autofiller_extension" / "fill-engine" / "dist" / "engine.js"
# The oldest app version the engine that main points at fits. Raise it in the PR that moves the pointer to an
# engine older apps can't run.
MIN_APP = Path(__file__).with_name("engine_min_app.txt")
# Where Apply holds the public key its builds are checked with (W0 moves Apply to its own repo: then read it there).
APP_KEY = ROOT / "apply-agent" / "src" / "apply" / "engine_download.py"


def public_key(private: Ed25519PrivateKey) -> str:
    raw = private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    return base64.b64encode(raw).decode()


def make_key(path: Path) -> str:
    """A new key pair: the private key written to `path` (never over a file), the public key returned."""
    private = Ed25519PrivateKey.generate()
    pem = private.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                serialization.NoEncryption())
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as file:
        file.write(pem)
    return public_key(private)


def load_key(path: Path) -> Ed25519PrivateKey:
    private = serialization.load_pem_private_key(path.read_bytes(), password=None)
    if not isinstance(private, Ed25519PrivateKey):
        raise SystemExit(f"{path} is not an Ed25519 private key")
    return private


def entry(bundle: bytes, private: Ed25519PrivateKey, min_app: str, now: datetime.datetime) -> dict:
    """builds.json's line for this bundle. Refuses one that names a source map: the maps stay on WorkIt."""
    if b"sourceMappingURL" in bundle:
        raise SystemExit("the bundle names a source map: build it without one")
    version(min_app)
    return {
        "sha256": hashlib.sha256(bundle).hexdigest(),
        "signature": base64.b64encode(private.sign(bundle)).decode(),
        "min_app": min_app,
        "published_at": now.isoformat(timespec="seconds"),
    }


def publish(storage, bundle: bytes, line: dict) -> list[dict] | None:
    """Uploads the bundle, then the list with its line last; the new list, or None when the list already ends with
    this bundle at this min_app. A bundle published before moves to the end, so an engine pointer moved back serves
    the older build again at this min_app; an app that a build of a higher min_app fits keeps that build."""
    bucket = storage.from_(BUCKET)
    builds = json.loads(bucket.download(INDEX)) if _has(bucket, INDEX) else []
    if builds and (builds[-1]["sha256"], builds[-1]["min_app"]) == (line["sha256"], line["min_app"]):
        return None
    if not _has(bucket, f"{line['sha256']}.js"):
        bucket.upload(f"{line['sha256']}.js", bundle, {"content-type": "application/javascript"})
    builds = [*(b for b in builds if b["sha256"] != line["sha256"]), line]
    bucket.upload(INDEX, json.dumps(builds, indent=1).encode(),
                  {"content-type": "application/json", "upsert": "true"})
    return builds


def check_app_holds(public: str) -> None:
    """Refuses a key whose public half isn't the one Apply checks builds with: no app would run what it signs."""
    held = re.search(r'^PUBLIC_KEY = "([^"]*)"$', APP_KEY.read_text(), re.MULTILINE) if APP_KEY.exists() else None
    if held is None:
        raise SystemExit(f"found no PUBLIC_KEY line in {APP_KEY}, so this can't check that Apply holds this key")
    if held[1] != public:
        raise SystemExit(f"Apply holds {held[1] or 'no engine key'} ({APP_KEY.name}'s PUBLIC_KEY), but this key's public"
                         f" half is {public}: no app would run this build. Put the right key in, or sign with the"
                         " one Apply holds")


def _has(bucket, name: str) -> bool:
    """Whether the bucket holds `name` (a listing gives 100 names at most, so it searches for this one)."""
    return any(item["name"] == name for item in bucket.list(options={"search": name}))


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)
    made = commands.add_parser("make-key")
    made.add_argument("path", type=Path)
    sent = commands.add_parser("publish")
    sent.add_argument("--key", type=Path, required=True)
    sent.add_argument("--min-app", default=MIN_APP.read_text().strip())
    sent.add_argument("--engine", type=Path, default=ENGINE)
    sent.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    if args.command == "make-key":
        print(f"Public key, for apply-agent/src/apply/engine_download.py PUBLIC_KEY: {make_key(args.path)}")
        return
    private = load_key(args.key)
    bundle = args.engine.read_bytes()
    line = entry(bundle, private, args.min_app, datetime.datetime.now(datetime.UTC))
    check_app_holds(public_key(private))
    print(f"Build {line['sha256'][:12]} ({len(bundle):,} bytes) for apps {args.min_app} and later,"
          f" signed by the key Apply holds")
    if args.dry_run:
        print("Dry run: nothing uploaded.")
        return
    from app.db import get_supabase  # only a real publish needs the service key

    try:
        builds = publish(get_supabase().storage, bundle, line)
    except SystemExit:
        raise
    except Exception as error:
        sys.exit(f"Storage refused it: {error}. Is the private {BUCKET} bucket made in the Supabase dashboard?")
    if builds is None:
        print(f"{INDEX} already ends with this build for apps {args.min_app} and later: nothing uploaded.")
    else:
        print(f"Published: {len(builds)} build(s) in {BUCKET}/{INDEX}.")


if __name__ == "__main__":
    main()
