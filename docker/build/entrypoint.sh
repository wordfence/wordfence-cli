#!/bin/bash
set -e

cd /root/wordfence-cli

ARCHITECTURE=$(dpkg --print-architecture)
VERSION=$(python3 -c "from wordfence import version; print(version.__version__)")
CHANGELOG_VERSION=$(head -n 1 /root/debian/changelog | sed -n -E 's/wordfence \(([^)]+)\).*/\1/p')

if [ "$CHANGELOG_VERSION" != "$VERSION" ]; then
  DEBFULLNAME=Wordfence
  DEBEMAIL=opensource@wordfence.com
  export DEBFULLNAME
  export DEBEMAIL
  echo "Changelog verison $CHANGELOG_VERSION does not equal pyproject.toml version $VERSION -- updating changelog"
  cd /root/debian
  dch \
    --distribution unstable \
    --check-dirname-level 0 \
    --package wordfence \
    --newversion "$VERSION" \
    "$VERSION release. See https://github.com/wordfence/wordfence-cli for release notes."
  cd /root/wordfence-cli
fi

# install requirements
pip install --upgrade pip
pip install -r requirements.txt

pyinstaller \
  --name wordfence \
  --onefile \
  --hidden-import wordfence.cli.scan \
  --hidden-import wordfence.cli.scan.config \
  --hidden-import wordfence.cli.configure \
  --hidden-import wordfence.cli.configure.definition \
  main.py

pushd /root/wordfence-cli/dist

# compress the standalone executable, checksum and sign it, and copy both to the output directory
STANDALONE_FILENAME="wordfence_${VERSION}_${ARCHITECTURE}_linux_exec"
tar -czvf "${STANDALONE_FILENAME}.tar.gz" wordfence
sha256sum "${STANDALONE_FILENAME}.tar.gz" > "${STANDALONE_FILENAME}.tar.gz.sha256"
gpg \
  --homedir "$CONTAINER_GPG_HOME_DIR" \
  --detach-sign \
  --armor \
  --local-user '=Wordfence <opensource@wordfence.com>' \
  "${STANDALONE_FILENAME}.tar.gz"
gpg \
  --homedir "$CONTAINER_GPG_HOME_DIR" \
  --detach-sign \
  --armor \
  --local-user '=Wordfence <opensource@wordfence.com>' \
  "${STANDALONE_FILENAME}.tar.gz.sha256"
cp \
  "${STANDALONE_FILENAME}.tar.gz" \
  "${STANDALONE_FILENAME}.tar.gz.asc" \
  "${STANDALONE_FILENAME}.tar.gz.sha256" \
  "${STANDALONE_FILENAME}.tar.gz.sha256.asc" \
  /root/output

popd

ls -lah "/root/output"
