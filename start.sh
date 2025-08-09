#!/bin/bash
set -e

TOKEN=$(snapctl get token)

if [ -z "$TOKEN" ]; then
    echo "TOKEN required"
    exit 1
fi

export TOKEN
python3 $SNAP/bin/thgbot.py "$@"
