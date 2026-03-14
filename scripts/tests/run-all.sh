#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)

cd "$ROOT_DIR"

PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q --tb=short

cd "$ROOT_DIR/frontend"
CI=true npm test -- --watchAll=false --runInBand \
  src/__tests__/systemProfileImportPage.render.test.js \
  src/__tests__/systemProfileBoardPage.v27.test.js \
  src/__tests__/serviceGovernancePage.render.test.js \
  src/__tests__/systemListConfigPage.v27.test.js \
  src/__tests__/navigationAndPageTitleRegression.test.js
