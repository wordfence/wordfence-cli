#!/bin/bash
set -e

cd /root/wordfence-cli

ARCHITECTURE=$(dpkg --print-architecture)
VERSION=$(python3 -c 'from wordfence import version; print(version.__version__)')
GPG_USER='=Wordfence <opensource@wordfence.com>'

# install build requirements
pip install --upgrade pip
pip install -r requirements.txt --force-reinstall

if [ "$PACKAGE_TYPE" = 'deb' ] || [ "$PACKAGE_TYPE" = 'all' ]; then

  # build deb package

  export DEBFULLNAME='Wordfence'
  export DEBEMAIL='opensource@wordfence.com'
  echo 'Generating changelog'
  dch \
    --distribution unstable \
    --check-dirname-level 0 \
    --package wordfence \
    --newversion "$VERSION" \
    --create \
    "${VERSION} release. See https://github.com/wordfence/wordfence-cli/releases/latest for release notes."

  # build the package
  dpkg-buildpackage -us -uc -b

  pushd ..

  # sign and generate checksum
  DEB_FILENAME="wordfence_${VERSION}_all"
  sha256sum "${DEB_FILENAME}.deb" > "${DEB_FILENAME}.deb.sha256"
  gpg \
    --homedir "$CONTAINER_GPG_HOME_DIR" \
    --detach-sign \
    --armor \
    --local-user "$GPG_USER" \
    "${DEB_FILENAME}.deb"
  gpg \
    --homedir "$CONTAINER_GPG_HOME_DIR" \
    --detach-sign \
    --armor \
    --local-user "$GPG_USER" \
    "${DEB_FILENAME}.deb.sha256"
  cp \
    "${DEB_FILENAME}.deb" \
    "${DEB_FILENAME}.deb.asc" \
    "${DEB_FILENAME}.deb.sha256" \
    "${DEB_FILENAME}.deb.sha256.asc" \
    /root/output

  popd

fi

if [ "$PACKAGE_TYPE" = 'standalone' ] || [ "$PACKAGE_TYPE" = 'all' ]; then

  # build standalone executable

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
    --local-user "$GPG_USER" \
    "${STANDALONE_FILENAME}.tar.gz"
  gpg \
    --homedir "$CONTAINER_GPG_HOME_DIR" \
    --detach-sign \
    --armor \
    --local-user "$GPG_USER" \
    "${STANDALONE_FILENAME}.tar.gz.sha256"
  cp \
    "${STANDALONE_FILENAME}.tar.gz" \
    "${STANDALONE_FILENAME}.tar.gz.asc" \
    "${STANDALONE_FILENAME}.tar.gz.sha256" \
    "${STANDALONE_FILENAME}.tar.gz.sha256.asc" \
    /root/output

  popd

fi

ls -lah /root/output
