#!/bin/bash

pip install toml

OLD_VERSION=$(<VERSION)
CURRENT_VERSION=$(python -c "import toml;print(toml.load('pyproject.toml')['tool']['poetry']['version'])")

if [ "$OLD_VERSION" = "$CURRENT_VERSION" ]; then
  echo "Version number in pyproject.toml has not been incremented. Skipping build."
  exit 2  # Return a special exit code
else
  echo $CURRENT_VERSION > VERSION
  exit 0
fi
