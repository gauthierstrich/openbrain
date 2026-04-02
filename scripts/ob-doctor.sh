#!/bin/bash
# Wrapper for python diagnostic script
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON=$(which python3 || echo "python3")
"$PYTHON" "$DIR/../core/doctor.py"
