"""Test setup: isolated data directory and offline agents."""

from __future__ import annotations

import os
import tempfile

os.environ["COSPAL_DATA_DIR"] = tempfile.mkdtemp(prefix="cospal-test-")
os.environ["COSPAL_OFFLINE"] = "1"
