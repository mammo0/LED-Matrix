ARG ALPINE_VERSION=3.18
FROM balenalib/raspberry-pi-alpine:$ALPINE_VERSION
ARG ALPINE_VERSION


ARG WHL_FILE
ARG PKG_VER
ARG PKG_REL
ARG PYTHON_DEPS
ARG BUILD_UID
ARG BUILD_GID


# install Alpine SDK for bulding packages
RUN apk update && \
    apk add alpine-sdk


# set build directory
ENV BUILD_DIR=/build
WORKDIR "$BUILD_DIR"


# create a new user for the build process
RUN getent group ${BUILD_GID} || addgroup -g ${BUILD_GID} bgroup && \
    group_name=$(getent group 100 | sed "s/:.*//") && \
    getent passwd ${BUILD_UID} || adduser -u ${BUILD_UID} -D -H -G ${group_name} buser


# add build files
ADD dist/*.whl "$BUILD_DIR"
ADD alpine/* "$BUILD_DIR"


# build the package
RUN abuild-keygen -a -n && \
    abuild -F checksum && \
    abuild -F -r && \
    # copy the created package back to the build directory
    cp /root/packages/**/*.apk "${BUILD_DIR}/" && \
    # set the right file permissions
    chown ${BUILD_UID}:${BUILD_GID} "${BUILD_DIR}"/*.apk


ENV OUT_DIR=/out
VOLUME ["$OUT_DIR"]
# simply copy the apk file to the mounted volume
CMD cp -p "${BUILD_DIR}"/*.apk "${OUT_DIR}/"
