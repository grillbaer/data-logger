#!/bin/bash

set -e

SCRIPT="$(realpath -s $0)"
SCRIPTDIR="$(dirname $SCRIPT)"
cd "$SCRIPTDIR"

exec python3 main.py
