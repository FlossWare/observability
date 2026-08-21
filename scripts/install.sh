#!/bin/bash
# Install observability-ai from GitHub
set -e
echo "Installing observability-ai..."
pip install "git+https://github.com/FlossWare/observability-ai.git"
echo "observability-ai installed successfully."
python3 -c "import observability_ai; print(f'Version: {observability_ai.__version__}')"
