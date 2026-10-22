#!/usr/bin/env python3
"""Backend acknowledgement: apply staged cursors only after records persist."""
import json
import sys
from cursor import CursorManager


def main():
    try:
        updates = json.load(sys.stdin)
        if not isinstance(updates, list) or len(updates) > 16:
            raise ValueError('Invalid cursor update batch')
        for update in updates:
            manager = CursorManager(update['namespace'], update['kind'], key=update['key'])
            manager.advance(update['value'])
        print(json.dumps({'success': True, 'updates': len(updates)}))
    except Exception as error:
        print(json.dumps({'success': False, 'error': f'{type(error).__name__}: {error}'}))
        sys.exit(1)


if __name__ == '__main__':
    main()
