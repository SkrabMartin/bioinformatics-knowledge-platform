#!/usr/bin/env python3
"""Create private local Compose configuration without printing credentials."""
import os
from pathlib import Path
import secrets

destination = Path(__file__).resolve().parents[1] / ".env.preview"
try:
    descriptor = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
except FileExistsError:
    raise SystemExit(".env.preview already exists; preserved unchanged.") from None
with os.fdopen(descriptor, "w") as output:
    output.write(f"POSTGRES_PASSWORD={secrets.token_hex(32)}\nBKP_PREVIEW_PORT=8088\n")
print("Created .env.preview (0600); credentials were not displayed.")
