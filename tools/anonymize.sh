#!/usr/bin/env bash
# Produce the anonymised review mirror from the named repository.
#
#   tools/anonymize.sh ../camf-anon
#
# The named repository is canonical: it is published first, so the defensive
# publication date starts running immediately. This script derives the mirror
# reviewers see. Running it by hand is what a checklist cannot guarantee --
# every step here is a step that has been forgotten by somebody before.

set -euo pipefail

DEST="${1:?usage: tools/anonymize.sh <destination>}"
SRC="$(cd "$(dirname "$0")/.." && pwd)"

REAL_NAME="Nikolay Posypanko"
REAL_EMAIL="nposypanko@gmail.com"
ANON="Anonymous Author(s)"

[ -e "$DEST" ] && { echo "refusing to overwrite existing $DEST" >&2; exit 1; }

git -C "$SRC" diff --quiet || { echo "working tree is dirty; commit first" >&2; exit 1; }
mkdir -p "$DEST"
git -C "$SRC" archive HEAD | tar -x -C "$DEST"          # tracked files only, no history

cd "$DEST"
rm -rf tools                                             # this script names the author

# Copyright lines
sed -i "s/Copyright \(20[0-9][0-9]\) $REAL_NAME/Copyright \1 $ANON/" LICENSE NOTICE

cat >> NOTICE <<'EOF'

Attribution is withheld for double-blind review and will be restored on
publication. The work is protected as an anonymous work under the Berne
Convention; the named repository and the archived release carry the authors'
identity.
EOF

# Citation metadata cannot be anonymised field by field without lying about
# the schema, so it is replaced wholesale.
cat > CITATION.cff <<'EOF'
cff-version: 1.2.0
title: "CAMF — Carbon Audit Matrix Format: reference implementation"
message: "Anonymised copy for double-blind review."
type: software
authors:
  - name: "Anonymous Author(s)"
license: Apache-2.0
EOF

# Anything that still names the author, the affiliation, a machine or an
# account is a hard stop -- the mirror is not written unless the tree is clean.
PATTERNS='claude|anthropic|Posypanko|posypanko|nposypanko|Eurasian|\bERG\b|winkers|\.mcp|/Users/|C:\\\\'
if grep -rInE --binary-files=without-match "$PATTERNS" . ; then
  echo "ANONYMISATION FAILED: the matches above must be removed" >&2
  exit 1
fi

git init -q
git add -A
git -c user.name="Anonymous" -c user.email="anonymous@example.invalid" \
    commit -q -m "CAMF reference implementation (anonymised for review)"

echo "mirror written to $DEST"
echo "remaining by hand: upload to the review mirror service, confirm its"
echo "lifetime covers the review cycle, and put the link in the paper."
