BASE_DIR:=$(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))


D_BUILD_IMAGE_TAG=matrix_venv_builder:latest
ALPINE_VENV_ARCHIVE=$(BASE_DIR)/resources/LED-Matrix_virtuelenv.tar.gz
CONFIG_FILE=$(BASE_DIR)/config.ini


$(ALPINE_VENV_ARCHIVE):
ifeq ("$(wildcard $(ALPINE_VENV_ARCHIVE))","")
	$(error "File $(ALPINE_VENV_ARCHIVE) not found!")
endif

$(CONFIG_FILE):
	@# create the config file if necessary
	$(BASE_DIR)/scripts/create_config.sh $(CONFIG_FILE)


build-alpine-venv:
	docker build --build-arg BUILD_UID=`id -u` \
				 --build-arg BUILD_GID=`id -g` \
				 -t $(D_BUILD_IMAGE_TAG) .
	docker run --rm -v $(BASE_DIR)/resources:/out $(D_BUILD_IMAGE_TAG)

install-alpine-venv: $(ALPINE_VENV_ARCHIVE)
	tar -zxvf $(ALPINE_VENV_ARCHIVE)

# target alias for creating the cofig file
config: $(CONFIG_FILE);

develop: $(CONFIG_FILE)
	FREETYPEPY_BUNDLE_FT=1 FREETYPEPY_WITH_LIBPNG=1 pipenv sync -d
