#!/usr/bin/env python3
"""The abstract-to-digest publisher is retired. Use the translation runner."""
import sys

print('Retired: run tools/run-daily.sh with the translation publisher configuration. '
      'Abstract expansion and generated expert quotations are disabled.', file=sys.stderr)
sys.exit(2)
