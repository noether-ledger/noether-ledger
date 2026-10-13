#!/usr/bin/env bash
# Run once in macOS Terminal from this folder:  ./setup_github.sh
# Step 1 (first run): creates a signing/auth key in ../noether-ledger-keys and prints the public key, then stops.
#   Add that public key to the GitHub account "noether-ledger" TWICE: Settings > SSH and GPG keys >
#   New SSH key, once as "Authentication Key" and once as "Signing Key". Create an empty repo noether-ledger/noether-ledger (no README).
# Step 2 (second run): re-signs the history with that key, in UTC, and pushes.
# Optional argument: the account's numeric noreply email (Settings > Emails), e.g. 123456789+noether-ledger@users.noreply.github.com
set -euo pipefail
KEYDIR="$(cd .. && pwd)/noether-ledger-keys"; KEY="$KEYDIR/id_ed25519"
if [ ! -f "$KEY" ]; then
  mkdir -p "$KEYDIR"; chmod 700 "$KEYDIR"
  ssh-keygen -q -t ed25519 -C "noether-ledger" -f "$KEY"     # set a passphrase when asked
  echo; echo "Add this public key to GitHub (Authentication AND Signing), then run this script again:"; cat "$KEY.pub"; exit 0
fi
EMAIL="${1:-noether-ledger@users.noreply.github.com}"
git config user.name "noether-ledger"
git config user.email "$EMAIL"
git config gpg.format ssh
git config gpg.ssh.program ssh-keygen
git config user.signingkey "$KEY.pub"
git config commit.gpgsign true
git config gpg.ssh.allowedSignersFile allowed_signers
git config core.sshCommand "ssh -i '$KEY' -o IdentitiesOnly=yes"
echo "$EMAIL $(cut -d' ' -f1,2 "$KEY.pub")" > allowed_signers
git add allowed_signers
NOW="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
# replaces the workspace's commit and its signature with one signed by your new key
TZ=UTC GIT_COMMITTER_DATE="$NOW" git commit --amend --no-edit --reset-author --date="$NOW"
git log --show-signature -1 | head -3
git remote get-url origin >/dev/null 2>&1 || git remote add origin git@github.com:noether-ledger/noether-ledger.git
ssh -i "$KEY" -o IdentitiesOnly=yes -T git@github.com 2>&1 | grep -q "Hi noether-ledger" || { echo "SSH auth is not noether-ledger: stop"; exit 1; }
git push -u origin main
echo "Done. Back up ../noether-ledger-keys and sealed/ (never push sealed/ before resolution)."
