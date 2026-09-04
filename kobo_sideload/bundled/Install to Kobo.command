#!/bin/bash
# Double-click on macOS. Right-click → Open if Gatekeeper complains.
cd -P -- "$(dirname -- "$0")" || exit 1
exec bash "./install.sh"
