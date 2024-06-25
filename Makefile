BASE_DIR:=$(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))

D_BUILD_IMAGE_TAG=localhost/led-matrix_apk_builder:latest
CONFIG_FILE=$(BASE_DIR)/config.ini


.PHONY: develop production config run build-alpine-package


build-alpine-package: ALL_DEPS:=$(shell poetry export -f requirements.txt --without-hashes --with config | sed "s/ ; .*//" | tr -d " " | tr "\n" " ")
build-alpine-package: ALPINE_DEPS:=$(shell poetry export -f requirements.txt --without-hashes --only alpine | sed "s/ ; .*//" | tr -d " " | tr "\n" " ")
build-alpine-package: INSTALL_DEPS:=$(filter-out $(ALPINE_DEPS), $(ALL_DEPS))
build-alpine-package: PKG_VER:=$(shell poetry version | cut -d " " -f2 | sed "s/\.post/_p/")
build-alpine-package: PKG_REL:=0
build-alpine-package: WHL_FILE:=$(shell echo led_matrix-`poetry version | cut -d " " -f2`-py3-none-any.whl)
build-alpine-package:
	poetry build -f wheel

	poetry install --only config
	poetry run create-config alpine/default_config.ini

	docker build --build-arg WHL_FILE=$(WHL_FILE) \
				 --build-arg PKG_VER=$(PKG_VER) \
				 --build-arg PKG_REL=$(PKG_REL) \
				 --build-arg BUILD_UID=`id -u` \
			     --build-arg BUILD_GID=`id -g` \
				 --build-arg PYTHON_DEPS="$(INSTALL_DEPS)" \
				 --platform "linux/arm/v6" \
			     -t $(D_BUILD_IMAGE_TAG) .
	docker run --rm -v $(BASE_DIR)/dist:/out $(D_BUILD_IMAGE_TAG)

# target alias for creating the config file
config:
	poetry install --only config
	@# create or update the config file if necessary
	poetry run create-config $(CONFIG_FILE)

develop: config
	poetry install --sync
	FREETYPEPY_BUNDLE_FT=1 FREETYPEPY_WITH_LIBPNG=1 poetry run pip install --force git+https://github.com/mammo0/freetype-py.git@led-matrix

production: config
	poetry install --without dev --sync
	FREETYPEPY_BUNDLE_FT=1 FREETYPEPY_WITH_LIBPNG=1 poetry run pip install --force git+https://github.com/mammo0/freetype-py.git@led-matrix

run:
	poetry run led-matrix $(CONFIG_FILE)
