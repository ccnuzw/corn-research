#!/usr/bin/env python3
"""Verify local backup inventory and SHA-256 without extracting or executing data."""
import argparse
import hashlib
import json
from pathlib import Path

REQUIRED_FILES = {'postgres.dump', 'redis.rdb', 'html-data.tar.gz', 'code-version.txt', 'image-ids.txt'}


def verify(directory):
    root = Path(directory)
    manifest_path = root / 'manifest.json'
    if manifest_path.is_symlink():
        raise ValueError('Manifest must not be a symlink')
    manifest = json.loads(manifest_path.read_text())
    if not isinstance(manifest, dict) or not REQUIRED_FILES.issubset(manifest):
        raise ValueError('Missing required backup artifacts')
    for name, expected in manifest.items():
        if not isinstance(name, str) or Path(name).name != name or name in ('.', '..'):
            raise ValueError('Invalid manifest path')
        path = root / name
        if path.is_symlink() or not path.is_file() or path.stat().st_size == 0:
            raise ValueError('Missing, empty or symlinked backup artifact: ' + name)
        if not isinstance(expected, str) or len(expected) != 64:
            raise ValueError('Invalid checksum: ' + name)
        digest = hashlib.sha256()
        with path.open('rb') as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b''):
                digest.update(chunk)
        if digest.hexdigest() != expected:
            raise ValueError('Checksum mismatch: ' + name)
    return len(manifest)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    try:
        count = verify(args.directory)
    except (OSError, ValueError, TypeError) as error:
        parser.exit(1, f'Backup verification failed: {error}\n')
    print(f'Backup checksums verified: {count} files (not a restore rehearsal)')


if __name__ == '__main__':
    main()
