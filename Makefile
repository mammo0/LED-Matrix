BASE_DIR:=$(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))
INSTALL_DIR=/usr/bin/ledmatrix
INITD_SERVICE=led-matrix
INITD_SCRIPT=$(BASE_DIR)/$(INITD_SERVICE)
INITD_DIR=/etc/init.d


D_BUILD_IMAGE_TAG=matrix_venv_builder:latest
ALPINE_VENV_ARCHIVE=$(BASE_DIR)/resources/LED-Matrix_virtuelenv.tar.gz
CONFIG_FILE=$(BASE_DIR)/config.ini


$(ALPINE_VENV_ARCHIVE):
ifeq ("$(wildcard $(ALPINE_VENV_ARCHIVE))","")
	$(error "File $(ALPINE_VENV_ARCHIVE) not found!")
endif


build-alpine-venv:
	docker build --build-arg BUILD_UID=`id -u` \
				 --build-arg BUILD_GID=`id -g` \
				 -t $(D_BUILD_IMAGE_TAG) .
	docker run --rm -v $(BASE_DIR)/resources:/out $(D_BUILD_IMAGE_TAG)

install-alpine-venv: $(ALPINE_VENV_ARCHIVE)
	tar -zxvf $(ALPINE_VENV_ARCHIVE)

# target alias for creating the cofig file
config:
	@# create or update the config file if necessary
	$(BASE_DIR)/scripts/create_config.py $(CONFIG_FILE)

develop: config
	FREETYPEPY_BUNDLE_FT=1 FREETYPEPY_WITH_LIBPNG=1 pipenv sync -d

production: config
	FREETYPEPY_BUNDLE_FT=1 FREETYPEPY_WITH_LIBPNG=1 pipenv sync

install:
	ln -s $(INSTALL_DIR) $(BASE_DIR)
	cp $(INITD_SCRIPT) $(INITD_DIR)/$(INITD_SERVICE)
	rc-update add $(INITD_SERVICE)

uninstall:
	rc-update del $(INITD_SERVICE)
	rm $(INITD_DIR)/$(INITD_SERVICE)
	rm $(INSTALL_DIR)
	

run:
ifeq ("$(wildcard $(BASE_DIR)/.venv)","")
	$(eval VENV_DIR:=$(shell pipenv --venv))
else
	$(eval VENV_DIR:=$(BASE_DIR)/.venv)
endif
	$(eval PYTHON=$(VENV_DIR)/bin/python)
	$(PYTHON) main.py
