FROM balenalib/raspberry-pi-alpine:3.12


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
            cmake \
            python3 \
            # alpine python dependencies
            $alpine_deps \
            # spidev dependencies
            python3-dev && \
    # install pip
    python3 -m ensurepip && \
    pip3 install --upgrade pip && \
    # install pipenv
    pip3 install pipenv


# add source code
ADD . "$BUILD_DIR"
WORKDIR "$BUILD_DIR"


# create virtual environment
RUN PIPENV_VENV_IN_PROJECT=1 PIPENV_SITE_PACKAGES=1 VIRTUALENV_ALWAYS_COPY=1 pipenv lock -r > "$VENV_REQ_FILE" && \
    # remove already installed alpine requirements from pip file
    for installed_dep in $(echo $ALPINE_PY_DEPS | tr ',' ' '); do \
        sed -i "/$installed_dep/d" "$VENV_REQ_FILE"; \
    done && \
    # install the remaining dependencies directly via pip
    FREETYPEPY_BUNDLE_FT=1 FREETYPEPY_WITH_LIBPNG=1 "$VIRTUALENV_DIR"/bin/pip install --no-build-isolation -r "$VENV_REQ_FILE"


VOLUME ["$OUT_DIR"]
COPY scripts/create_virtualenv_archive.sh /bin/
ENTRYPOINT ["create_virtualenv_archive.sh"]
