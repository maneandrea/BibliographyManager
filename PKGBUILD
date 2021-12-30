# Maintainer: Andrea Manenti <andrea [dot] manenti [at] yahoo [dot] com>

pkgname=bibmanager
pkgver=35.fb0eebc
pkgrel=1
pkgdesc="Tool for managing a BibTeX bibliography file tailored for High Energy Theory "
arch=(any)
license=('GPL')
depends=('python-pillow' 'python-sympy')
makedepends=('git')
source=('git+https://github.com/maneandrea/BibliographyManager.git'
        'bibmanager.config')
sha256sums=('SKIP'
            'd12b08616f689a924ab869dbb8ce69eaeed126f58fb021c5bd37028b52cf342e')

pkgver() {
        cd "$srcdir"/BibliographyManager
        echo `git rev-list --count master`.`git rev-parse --short master`
}

build() {
    cd "$srcdir"/BibliographyManager
}

package() {
    cd "$srcdir"/BibliographyManager

    install -vDm 755 bin/bibmanager "$pkgdir"/usr/bin/bibmanager

    _pyver=$(python -V | sed -e 's/Python \([0-9]\.[0-9]\+\)\..*/\1/')
    _pypath="${pkgdir}/usr/lib/python${_pyver}/site-packages/bibmanager"

    mkdir -p $_pypath

    install -vDm 644 src/biblioDB.py $_pypath/biblioDB.py
    install -vDm 644 src/biblioGUI.py $_pypath/biblioGUI.py
    install -vDm 644 src/otherWidgets.py $_pypath/otherWidgets.py
    install -vDm 644 src/inspireQuery.py $_pypath/inspireQuery.py
    install -vDm 755 src/bibmanager.py $_pypath/bibmanager.py
    install -vDm 644 Icons/icon.ico ${pkgdir}/usr/share/pixmaps/bibmanager.ico
    install -vDm 644 Icons/icon.png ${pkgdir}/usr/share/pixmaps/bibmanager.png

    mkdir -p $_pypath/Icons
    ln -sf /usr/share/pixmaps/bibmanager.png $_pypath/Icons/icon.png

    install -vDm 644 bibmanager.desktop ${pkgdir}/usr/share/applications/bibmanager.desktop

    install -vDm 644 bibmanager.config ${pkgdir}/tmp/bibmanager.config

    msg2 "Now, to put the config file do mkdir -p ~/.config/bibmanager && install -vDm 644 /tmp/bibmanager.config ~/.config/bibmanager/"


}

