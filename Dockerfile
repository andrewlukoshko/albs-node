FROM almalinux:8

RUN dnf install -y epel-release
RUN dnf upgrade -y
COPY ./buildnode.repo /etc/yum.repos.d/buildnode.repo
RUN dnf install -y --enablerepo="powertools" --enablerepo="epel" --enablerepo="buildnode" \
    python3 gcc gcc-c++ python3-devel python3-virtualenv cmake \
    python3-pycurl libicu libicu-devel python3-lxml git tree mlocate mc createrepo_c \
    python3-createrepo_c xmlsec1-openssl-devel \
    kernel-rpm-macros python3-libmodulemd dpkg-dev mock debootstrap pbuilder apt apt-libs \
    python3-apt keyrings-filesystem ubu-keyring debian-keyring raspbian-keyring qemu-user-static

RUN dnf clean all

RUN mkdir -p \
    /srv/alternatives/castor/build_node \
    /var/cache/pbuilder/aptcache/ \
    /var/cache/pbuilder/pbuilder_envs/ \
    /srv/alternatives/castor/build_node/pbuilder_envs/buster-amd64/aptcache \
    /srv/alternatives/castor/build_node/pbuilder_envs/bionic-amd64/aptcache \
    /srv/alternatives/castor/build_node/pbuilder_envs/focal-amd64/aptcache \
    /srv/alternatives/castor/build_node/pbuilder_envs/jessie-amd64/aptcache \
    /srv/alternatives/castor/build_node/pbuilder_envs/stretch-amd64/aptcache \
    /srv/alternatives/castor/build_node/pbuilder_envs/xenial-amd64/aptcache \
    /srv/alternatives/castor/build_node/pbuilder_envs/buster-arm64/aptcache \
    /srv/alternatives/castor/build_node/pbuilder_envs/buster-armhf/aptcache \
    /srv/alternatives/castor/build_node/pbuilder_envs/raspbian-armhf/aptcache \
    /srv/alternatives/castor/build_node/mock_configs \
    /root/.config/castor/build_node \
    /root/.config/cl-alternatives/

WORKDIR /build-node
COPY ./build_node /build-node/build_node
COPY almalinux_build_node.py /build-node/almalinux_build_node.py
COPY requirements.txt /build-node/requirements.txt

RUN python3 -m venv --system-site-packages env
RUN /build-node/env/bin/pip install --upgrade pip
RUN /build-node/env/bin/pip install -r requirements.txt
RUN /build-node/env/bin/pip cache purge

# COPY ./tests /build-node/tests
# RUN /build-node/env/bin/py.test tests

CMD ["/build-node/env/bin/python", "/build-node/almalinux_build_node.py"]
