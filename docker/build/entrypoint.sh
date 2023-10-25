#!/bin/bash
set -e

cd /root/wordfence-cli

# build deb package

ARCHITECTURE=$(dpkg --print-architecture)
VERSION=$(python3 -c "from wordfence import version; print(version.__version__)")
# CHANGELOG_VERSION=$(head -n 1 /root/wordfence-cli/debian/changelog | sed -n -E 's/wordfence \(([^)]+)\).*/\1/p')

export DEBFULLNAME=Wordfence
export DEBEMAIL=opensource@wordfence.com
echo "Generating changelog"
dch \
  --distribution unstable \
  --check-dirname-level 0 \
  --package wordfence \
  --newversion "$VERSION" \
  --create \
  "$VERSION release. See https://github.com/wordfence/wordfence-cli for release notes."

# install newer version of setuptools
python3 -m pip install setuptools --force-reinstall

# build the package
dpkg-buildpackage -us -uc -b

# build standalone executable

# install requirements
pip install --upgrade pip
pip install -r requirements.txt

pyinstaller \
  --name wordfence \
  --onefile \
  --hidden-import wordfence.cli.configure.configure \
  --hidden-import wordfence.cli.configure.definition \
  --hidden-import wordfence.cli.malwarescan.malwarescan \
  --hidden-import wordfence.cli.malwarescan.definition \
  --hidden-import wordfence.cli.vulnscan.vulnscan \
  --hidden-import wordfence.cli.vulnscan.definition \
  --hidden-import wordfence.cli.help.help \
  --hidden-import wordfence.cli.help.definition \
  --hidden-import wordfence.cli.version.version \
  --hidden-import wordfence.cli.version.definition \
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
