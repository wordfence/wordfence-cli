#!/bin/bash
set -e

cd /root/wordfence-cli

if [ "$PACKAGE_TYPE" = 'deb' ]; then

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

if [ "$PACKAGE_TYPE" = 'rpm' ]; then

  # build RPM package

  VERSION=$(python3 -c 'from wordfence import version; print(version.__version__)')
  SPECFILE="wordfence.spec"

  export PATH="${PATH}:/usr/local/bin"

  # setup directories for rpmbuild
  rpmdev-setuptree

  # create source archive for rpmbuild
  tar -C /root -czvf "/root/v${VERSION}.tar.gz" wordfence-cli
  cp "/root/v${VERSION}.tar.gz" /root/rpmbuild/SOURCES/
  cp "$SPECFILE" /root/rpmbuild/SPECS/

  # build RPM
  rpmbuild -bb \
    -D "wordfence_version ${VERSION}" \
    "/root/rpmbuild/SPECS/${SPECFILE}"

  # copy to output volume
  pushd /root/rpmbuild/RPMS/noarch/
  RPM_FILENAME="python3.11-wordfence-${VERSION}-1.el9.noarch"
  cp "${RPM_FILENAME}.rpm" /root/output/wordfence-el9.rpm
fi

if [ "$PACKAGE_TYPE" = 'standalone' ]; then

  # build standalone executable
  
  ARCHITECTURE=$(dpkg --print-architecture)
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
    --hidden-import wordfence.cli.remediate.remediate \
    --hidden-import wordfence.cli.remediate.definition \
    --hidden-import wordfence.cli.countsites.countsites \
    --hidden-import wordfence.cli.countsites.definition \
    main.py

  # compress and copy to output volume
  pushd /root/wordfence-cli/dist
  STANDALONE_FILENAME="wordfence_${VERSION}_${ARCHITECTURE}_linux_exec"
  tar -czvf "${STANDALONE_FILENAME}.tar.gz" wordfence
  cp "${STANDALONE_FILENAME}.tar.gz" "/root/output/wordfence_${ARCHITECTURE}.tar.gz"
  popd

fi

ls -lah /root/output
