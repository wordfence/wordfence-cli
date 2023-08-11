#!/bin/bash
set -e

#if [ ! -f /opt/keys/signing-key.asc ]; then
#    echo "Unable to locate the signing key"
#    exit 1
#fi

cd /opt/wordfence-cli

ARCHITECTURE=$(dpkg --print-architecture)
VERSION=$(python -c "from wordfence import version; print(version.__version__)")
CHANGELOG_VERSION=$(head -n 1 /opt/debian/changelog | sed -n -E 's/wordfence \(([^)]+)\).*/\1/p')

if [ "$CHANGELOG_VERSION" != "$VERSION" ]; then
  DEBFULLNAME=Wordfence
  DEBEMAIL=devs@wordfence.com
  export DEBFULLNAME
  export DEBEMAIL
  echo "Changelog verison $CHANGELOG_VERSION does not equal pyproject.toml version $VERSION -- updating changelog"
  cd /opt/debian
  dch \
    --distribution unstable \
    --check-dirname-level 0 \
    --package wordfence \
    --newversion "$VERSION" \
    "$VERSION release. See https://github.com/wordfence/wordfence-cli for release notes."
  cd /opt/wordfence-cli
fi

# install requirements
pip install --upgrade pip
pip install -r requirements.txt

pyinstaller \
  --name wordfence \
  --onefile \
  --hidden-import wordfence.cli.scan \
  --hidden-import wordfence.cli.scan.config \
  main.py

pushd /opt/wordfence-cli/dist

# compress the standalone executable, checksum it, and copy both to the output directory
STANDALONE_FILENAME="wordfence_${VERSION}_${ARCHITECTURE}_linux_exec"
tar -czvf "${STANDALONE_FILENAME}.tar.gz" wordfence
sha256sum "${STANDALONE_FILENAME}.tar.gz" > "${STANDALONE_FILENAME}.tar.gz.sha256"
cp "${STANDALONE_FILENAME}.tar.gz" "${STANDALONE_FILENAME}.tar.gz.sha256" /opt/output

popd

# keep the debian folder clean (additional files will be added as part of the build process)
#cp -r /opt/debian /opt/wordfence-cli/dist/debian
#cd /opt/wordfence-cli/dist

# build the package
#dpkg-buildpackage -us -uc -b

# set up GPG for signing
#gpg --import /opt/keys/signing-key.asc
#GPG_ID=$(gpg --list-signatures --with-colons | grep sig | head -n 1 | cut -d':' -f5)

# setting GPG_TTY environment variable resolves an error with dpkg-sig
#GPG_TTY=$(tty)
#export GPG_TTY

#echo "signing /opt/wordfence-cli/wordfence_${VERSION}_${ARCHITECTURE}.deb"
# sign using one of the below strategies
# debsigs --sign=origin -k "$GPG_ID" "/opt/wordfence-cli/wordfence_${VERSION}_${ARCHITECTURE}.deb"
#dpkg-sig -k "$GPG_ID" --sign builder "/opt/wordfence-cli/wordfence_${VERSION}_${ARCHITECTURE}.deb"

#cp "/opt/wordfence-cli/wordfence_${VERSION}_${ARCHITECTURE}.deb" "/opt/output/"
ls -lah "/opt/output"
