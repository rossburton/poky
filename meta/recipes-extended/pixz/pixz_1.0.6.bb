SUMMARY = "Parallel, indexed xz compressor"

DEPENDS = "xz libarchive"

SRC_URI = "https://github.com/vasi/pixz/releases/download/v${PV}/${BPN}-${PV}.tar.xz"
SRC_URI[md5sum] = "f6dc5909c9a31b192f69aa397ae8df48"
SRC_URI[sha256sum] = "02c50746b134fa1b1aae41fcc314d7c6f1919b3d48bcdea01bf11769f83f72e8"

LICENSE = "BSD-2-Clause"
LIC_FILES_CHKSUM = "file://LICENSE;md5=5cf6d164086105f1512ccb81bfff1926"

SRC_URI += "file://936d8068ae19d95260d3058f41dd6cf718101cd6.patch"

EXTRA_OECONF += "--without-manpage"

CACHED_CONFIGUREVARS += "ac_cv_file_src_pixz_1=no"

inherit autotools pkgconfig

BBCLASSEXTEND = "native"
