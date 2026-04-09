#!/bin/bash
set -euo pipefail
exec uvicorn src.api.app:app --host 0.0.0.0 --port 8400
