# Maintainer: Andrea Manenti <andrea [dot] manenti [at] yahoo [dot] com>

pkgname=bibmanager
pkgver=34.3f9f876
pkgrel=1
pkgdesc="Tool for managing a BibTeX bibliography file tailored for High Energy Theory "
arch=(any)
license=('GPL')
depends=('python-pillow' 'python-sympy')
makedepends=('git')
source=('git+https://github.com/maneandrea/BibliographyManager.git'
        'bibmanager.desktop')
sha256sums=('SKIP'
            '5a3503a4522877c7a83f6b7555d91999b8832a4e4b6222e622fe755d5f9b6168')

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

    cd "$srcdir"

    install -vDm 644 bibmanager.desktop ${pkgdir}/usr/share/applications/bibmanager.desktop

}

