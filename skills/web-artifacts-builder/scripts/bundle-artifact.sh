#!/usr/bin/env bash
#
# bundle-artifact.sh
# Bundle the current React project into a single self-contained bundle.html
# (all JS/CSS inlined) using Parcel + html-inline. Run from the project root
# (must contain index.html).
#
set -euo pipefail

if [ ! -f index.html ]; then
  echo "ERROR: run this from a project root containing index.html" >&2
  exit 1
fi

echo "==> Installing bundling dependencies"
npm install --no-fund --no-audit -D parcel @parcel/config-default parcel-resolver-tspaths html-inline

# Parcel config with path-alias (@/) support.
cat > .parcelrc <<'EOF'
{
  "extends": "@parcel/config-default",
  "resolvers": ["parcel-resolver-tspaths", "..."]
}
EOF

echo "==> Building with Parcel"
rm -rf dist .parcel-cache
npx parcel build index.html --no-source-maps --dist-dir dist --public-url ./

echo "==> Inlining into bundle.html"
npx html-inline -i dist/index.html -o bundle.html

echo "==> Created $(pwd)/bundle.html"
