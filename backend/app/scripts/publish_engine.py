"""
Publish a Fill engine build for WorkIt Auto Apply to download (KAN-836, W7
of docs/desktop_application_auto_apply.md; app/services/engine_builds.py).

Run by hand, never in CI:

  uv run python -m app.scripts.publish_engine make-key <private key file>
      A new Ed25519 engine key: the private key to that file (mode 600,
      never over an old one), and the public key printed, for Apply's
      `engine_download.PUBLIC_KEY`. Done once. Keep the file outside every
      checkout; whoever holds it can make every app run their code.

  uv run python -m app.scripts.publish_engine publish --key <file> --min-app 0.1.0 [--engine <dist/engine.js>] [--dry-run]
      Signs the engine bundle (the submodule's dist/engine.js by default),
      uploads it to the private `ApplyEngine` bucket as <sha256>.js and adds
      it to builds.json. Apps at --min-app or later get it from their next
      launch (within engine_builds.INDEX_TTL of the API reading it). A build
      that would break older apps gets a higher --min-app, so they keep the
      build before it. It prints the key's public half: it must be the one
      Apply holds, or every app refuses the build.

It writes to the Storage of the Supabase project the root .env names, as
the import does to its database: the user runs it, never Claude. The
`ApplyEngine` bucket is made once in the Supabase dashboard (Storage, New
bucket, Public off; app/routers/CLAUDE.md).
"""

import argparse
import base64
import datetime
import hashlib
import json
import os
import sys
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from app.services.engine_builds import BUCKET, INDEX, version

ENGINE = Path(__file__).resolve().parents[3] / "autofiller_extension" / "fill-engine" / "dist" / "engine.js"


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


def publish(storage, bundle: bytes, line: dict) -> list[dict]:
    """Uploads the bundle, then the list with its line added; the new list."""
    bucket = storage.from_(BUCKET)
    builds = json.loads(bucket.download(INDEX)) if _has(bucket, INDEX) else []
    if any(b["sha256"] == line["sha256"] for b in builds):
        raise SystemExit(f"this bundle is already published ({line['sha256'][:12]})")
    if not _has(bucket, f"{line['sha256']}.js"):
        bucket.upload(f"{line['sha256']}.js", bundle, {"content-type": "application/javascript"})
    builds = [*builds, line]
    bucket.upload(INDEX, json.dumps(builds, indent=1).encode(),
                  {"content-type": "application/json", "upsert": "true"})
    return builds


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
    sent.add_argument("--min-app", required=True)
    sent.add_argument("--engine", type=Path, default=ENGINE)
    sent.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    if args.command == "make-key":
        print(f"Public key, for apply-agent/src/apply/engine_download.py PUBLIC_KEY: {make_key(args.path)}")
        return
    private = load_key(args.key)
    bundle = args.engine.read_bytes()
    line = entry(bundle, private, args.min_app, datetime.datetime.now(datetime.UTC))
    print(f"Build {line['sha256'][:12]} ({len(bundle):,} bytes) for apps {args.min_app} and later,"
          f" signed by the key whose public half is {public_key(private)}")
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
    print(f"Published: {len(builds)} build(s) in {BUCKET}/{INDEX}.")


if __name__ == "__main__":
    main()
