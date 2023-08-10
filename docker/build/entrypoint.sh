#!/bin/bash
set -e

#if [ ! -f /opt/keys/signing-key.asc ]; then
#    echo "Unable to locate the signing key"
#    exit 1
#fi

cd /opt/wordfence-cli

ARCHITECTURE=$(dpkg --print-architecture)
VERSION=$(./setup.py --version)
CHANGELOG_VERSION=$(head -n 1 /opt/debian/changelog | sed -n -E 's/wordfence \(([^)]+)\).*/\1/p')

if [ "$CHANGELOG_VERSION" != "$VERSION" ]; then
  DEBFULLNAME=Wordfence
  DEBEMAIL=devs@wordfence.com
  export DEBFULLNAME
  export DEBEMAIL
  echo "Changelog verison $CHANGELOG_VERSION does not equal setup.py version $VERSION -- updating changelog"
  cd /opt/debian
  dch \
    --distribution unstable \
    --check-dirname-level 0 \
    --package wordfence \
    --newversion "$VERSION" \
    "$VERSION release. See https://github.com/wordfence/wordfence-cli for release notes."
  cd /opt/wordfence-cli
fi

pip install --upgrade pip setuptools wheel pyinstaller
pip install -r requirements.txt
python3 setup.py build
python3 setup.py install

pyinstaller \
  --name wordfence \
  --onefile \
  --hidden-import wordfence.cli.scan \
  --hidden-import wordfence.cli.scan.config \
  main.py

# copy the tar.gz file to the output directory
tar \
  -czvf "/opt/wordfence-cli/dist/wordfence_${VERSION}_${ARCHITECTURE}_linux_exec.tar.gz" \
  -C /opt/wordfence-cli/dist/ \
  wordfence
cp "/opt/wordfence-cli/dist/wordfence_${VERSION}_${ARCHITECTURE}_linux_exec.tar.gz" "/opt/output/"

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
