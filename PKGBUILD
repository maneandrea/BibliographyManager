# Maintainer: Andrea Manenti <andrea [dot] manenti [at] yahoo [dot] com>

pkgname=bibmanager
pkgver=36.edc3bf3
pkgrel=1
pkgdesc="Tool for managing a BibTeX bibliography file tailored for High Energy Theory "
arch=(any)
license=('GPL')
depends=('python-pillow' 'python-sympy')
makedepends=('git')
install=copy_config.install
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
    install -vDm 644 Icons/arxiv.png $_pypath/Icons/arxiv.png
    install -vDm 644 Icons/inspire.png $_pypath/Icons/inspire.png
    install -vDm 644 Icons/update.png $_pypath/Icons/update.png
    install -vDm 644 Icons/bibtex.png $_pypath/Icons/bibtex.png
    install -vDm 644 Icons/pdf.png $_pypath/Icons/pdf.png

    install -vDm 644 bibmanager.desktop ${pkgdir}/usr/share/applications/bibmanager.desktop

    cd "$srcdir"

    mkdir -p ${pkgdir}/tmp/
    cp bibmanager.config ${pkgdir}/tmp/bibmanager.config

}

