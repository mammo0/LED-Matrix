ARG ALPINE_VERSION=3.15
FROM balenalib/raspberry-pi-alpine:$ALPINE_VERSION
ARG ALPINE_VERSION


ARG BUILD_UID=1000
ARG BUILD_GID=1000
ARG BUILD_DIR=/build


# these variables are used by the 'create_package.sh' script
ENV OUT_DIR=/out
ENV VIRTUALENV_DIR=$BUILD_DIR/.venv
ENV BUILD_UID=$BUILD_UID
ENV BUILD_GID=$BUILD_GID


# these dependencies are part of the alpine community repository
# so install them through apk, not pip
# this reduces the build time
ARG ALPINE_PY_DEPS="numpy,pillow,bottle"
# this is a temporary file created by pipenv to install the remaining dependencies via pip
ARG VENV_REQ_FILE=$BUILD_DIR/resources/requirements.pip


# install dependencies
RUN alpine_deps='' && \
    for dep in $(echo $ALPINE_PY_DEPS | tr ',' ' '); do \
        alpine_deps="py3-$dep $alpine_deps"; \
    done && \
    apk update && \
    apk add alpine-sdk \
            # Python
            python3 \
            # alpine python dependencies
            $alpine_deps \
            # spidev dependencies
            python3-dev \
            # freetype-py dependencies
            cmake \
            openssl-dev && \
    # install all build dependencies of the pre-installed Alpine Python packages
    # if pip still needs to build a package later, all required dependencies are installed and the build process will not fail
    cd $(mktemp -d) && \
    for dep in $(echo $ALPINE_PY_DEPS | tr ',' ' '); do \
        # first try main repository
        curl -f "https://git.alpinelinux.org/aports/plain/main/py3-$dep/APKBUILD?h=$ALPINE_VERSION-stable" -o APKBUILD | \
            # if that fails, try the community repository
            curl -f "https://git.alpinelinux.org/aports/plain/community/py3-$dep/APKBUILD?h=$ALPINE_VERSION-stable" -o APKBUILD; \
        abuild -F deps; \
        rm APKBUILD; \
    done && \
    # install pip
    python3 -m ensurepip && \
    pip3 install --upgrade pip && \
    # install pipenv
    pip3 install pipenv


# add source code
ADD . "$BUILD_DIR"
WORKDIR "$BUILD_DIR"


# create virtual environment
RUN PIPENV_VENV_IN_PROJECT=1 PIPENV_SITE_PACKAGES=1 VIRTUALENV_ALWAYS_COPY=1 pipenv requirements > "$VENV_REQ_FILE" && \
    # remove already installed alpine requirements from pip file
    for installed_dep in $(echo $ALPINE_PY_DEPS | tr ',' ' '); do \
        sed -i "/$installed_dep/d" "$VENV_REQ_FILE"; \
    done && \
    # install the remaining dependencies directly via pip
    FREETYPEPY_BUNDLE_FT=1 FREETYPEPY_WITH_LIBPNG=1 "$VIRTUALENV_DIR"/bin/pip install --no-build-isolation -r "$VENV_REQ_FILE"


VOLUME ["$OUT_DIR"]
COPY scripts/create_virtualenv_archive.sh /bin/
ENTRYPOINT ["create_virtualenv_archive.sh"]
