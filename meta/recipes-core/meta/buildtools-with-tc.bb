DESCRIPTION = "This recipe is used to extend the functionality of buildtools-tarball \
               by adding the test harness plus binaries that might be required for DUTs.\
              "

require ${COREBASE}/meta/recipes-core/meta/buildtools-tarball.bb
inherit testimage

SDK_TITLE += "with test cases and binaries"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COREBASE}/LICENSE;md5=4d92cd373abda3937c2bc47fbc49d690 \
                    file://${COREBASE}/meta/COPYING.MIT;md5=3da9cfbcb788c80a0384361b4de20420"

TEST_EXPORT_ONLY = "1"
TEST_TARGET = "simpleremote"
IMAGE_NO_MANIFEST = "1"

addtask testimage before do_populate_sdk

tar_sdk_prepend () {
  mkdir ${SDK_OUTPUT}${SDKPATH}/exported_tests 2>/dev/null
  for i in $(ls ${TEST_EXPORT_DIR})
  do
    if [ ${i} != "tar_files" ]
    then
      cp -r ${TEST_EXPORT_DIR}/${i} ${SDK_OUTPUT}${SDKPATH}/exported_tests
    fi
  done
  sed -i 's/\"pkgmanifest\": \"\"/\"pkgmanifest\": \"\\ndropbear\\n\"/' ${SDK_OUTPUT}${SDKPATH}/exported_tests/testdata.json
  cp ${SDK_OUTPUT}${SDKPATH}/exported_tests/testdata.json ${TEST_EXPORT_DIR}
}

create_shar_append () {
  message='echo "To run exported tests, go into exported_tests directory and run ./runexported.py"'
  sed -i "/exit\ 0/i \
${message}" ${SDK_DEPLOY}/${TOOLCHAIN_OUTPUTNAME}.sh
}

