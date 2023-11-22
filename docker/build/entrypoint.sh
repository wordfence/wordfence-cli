#!/bin/bash
set -e

cd /root/wordfence-cli

ARCHITECTURE=$(dpkg --print-architecture)

if [ "$PACKAGE_TYPE" = 'deb' ] || [ "$PACKAGE_TYPE" = 'all' ]; then

  # build deb package

  VERSION=$(python3 -c 'from wordfence import version; print(version.__version__)')

  # install build requirements
  python3 -m pip install --upgrade pip
  python3 -m pip install -r requirements.txt --force-reinstall

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

  # copy to output volume
  pushd ..
  DEB_FILENAME="wordfence_${VERSION}_all"
  cp "${DEB_FILENAME}.deb" /root/output/wordfence.deb
  popd

fi

if [ "$PACKAGE_TYPE" = 'standalone' ] || [ "$PACKAGE_TYPE" = 'all' ]; then

  # build standalone executable
  
  VERSION=$(python3.8 -c 'from wordfence import version; print(version.__version__)')

  # install build requirements
  python3.8 -m pip install --upgrade pip
  python3.8 -m pip install -r requirements.txt --force-reinstall
  # Ubuntu 18.04 requires this additional package (as well as the OS package libffi-dev)
  python3.8 -m pip install cffi

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
    --hidden-import wordfence.cli.terms.terms \
    --hidden-import wordfence.cli.terms.definition \
    main.py

  # compress and copy to output volume
  pushd /root/wordfence-cli/dist
  STANDALONE_FILENAME="wordfence_${VERSION}_${ARCHITECTURE}_linux_exec"
  tar -czvf "${STANDALONE_FILENAME}.tar.gz" wordfence
  cp "${STANDALONE_FILENAME}.tar.gz" "/root/output/wordfence_${ARCHITECTURE}.tar.gz"
  popd

fi

ls -lah /root/output
