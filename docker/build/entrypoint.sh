#!/usr/bin/bash

if [ ! -f /opt/keys/signing-key.asc ]; then
echo "Unable to locate the signing key"
exit 1
fi

gpg --import /opt/keys/signing-key.asc

# grab the first GPG key ID
GPG_ID=$(gpg --list-signatures --with-colons | grep sig | head -n 1 | cut -d':' -f5)

cd /opt/wordfence-cli || exit 2
pip install --upgrade pip
pip install --upgrade setuptools
pip install -r requirements.txt
python3 setup.py build
python3 setup.py install

python3 setup.py --command-packages=stdeb.command bdist_deb

# setting GPG_TTY environment variable resolves an error with dpkg-sig
GPG_TTY=$(tty)
export GPG_TTY

# pick one signing strategy below
# debsigs --sign=origin -k "$GPG_ID" /opt/wordfence-cli/deb_dist/*.deb
dpkg-sig -k "$GPG_ID" --sign builder /opt/wordfence-cli/deb_dist/*.deb

cp /opt/wordfence-cli/deb_dist/*.deb /opt/output/
ls -lah /opt/output/*.deb
