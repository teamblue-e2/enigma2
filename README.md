## Our buildserver is currently running on: ##

> Ubuntu 22.04 LTS 

## teamBlue 7.3 (based on openPLi) is build using oe-alliance build-environment "7.3" and several git repositories: ##

> [https://github.com/oe-alliance/oe-alliance-core/tree/5.3](https://github.com/oe-alliance/oe-alliance-core/tree/5.3 "OE-Alliance")
>
> [https://github.com/teamblue-e2/enigma2/tree/7.3](https://github.com/teamblue-e2/enigma2/tree/7.3 "teamBlue E2")
>
> [https://github.com/teamblue-e2/skin/tree/master](https://github.com/teamblue-e2/skin/tree/master "teamBlue Skin")

> and a lot more...


----------

# Building Instructions #

1. Install required packages

    ```sh
    sudo apt-get install -y autoconf automake bison bzip2 chrpath coreutils cpio curl cvs debianutils default-jre default-jre-headless diffstat flex g++ gawk gcc gcc-12 gcc-multilib g++-multilib gettext git git-core gzip help2man info iputils-ping java-common libc6-dev libegl1-mesa libglib2.0-dev libncurses5-dev libperl4-corelibs-perl libproc-processtable-perl libsdl1.2-dev libserf-dev libtool libxml2-utils make ncurses-bin patch perl pkg-config psmisc python3 python3-git python3-jinja2 python3-pexpect python3-pip python-setuptools qemu quilt socat sshpass subversion tar texi2html texinfo unzip wget xsltproc xterm xz-utils zip zlib1g-dev zstd fakeroot lz4
    ```

1. Set `python3` as preferred provider for `python`

    ```sh
    sudo update-alternatives --install /usr/bin/python python /usr/bin/python2 1

    sudo update-alternatives --install /usr/bin/python python /usr/bin/python3 2

    sudo update-alternatives --config python
    ↳ Select python3
    ```

1. Set your shell to `/bin/bash`

    ```sh
    sudo dpkg-reconfigure dash
    ↳ Select "NO" when asked "Install dash as /bin/sh?"
    ```

1. Modify `max_user_watches`

    ```sh
    echo fs.inotify.max_user_watches=524288 | sudo tee -a /etc/sysctl.conf

    sudo sysctl -n -w fs.inotify.max_user_watches=524288
    ```

1. Add new user `teambluebuilder`

    ```sh
    sudo adduser teambluebuilder
    ```

1. Switch to new user `teambluebuilder`

    ```sh
    su - teambluebuilder
    ```

1. Create folder teamblue73

    ```sh
    mkdir -p teamblue73
    ```

1. Switch to folder teamblue73

    ```sh
    cd teamblue73
    ```

1. Clone oe-alliance repository

    ```sh
    git clone https://github.com/oe-alliance/build-enviroment.git -b 5.3
    ```

1. Switch to folder build-enviroment

    ```sh
    cd build-enviroment
    ```

1. Update build-enviroment

    ```sh
    make update
    ```

1. Finally, you can either:

* Build an image with feed (build time 5-12h)

    ```sh
    MACHINE=gbquad4k DISTRO=teamblue DISTRO_TYPE=release make image
    ```

* Build an image without feed (build time 1-2h)

    ```sh
    MACHINE=gbquad4k DISTRO=teamblue DISTRO_TYPE=release make enigma2-image
    ```

* Build the feeds

    ```sh
    MACHINE=gbquad4k DISTRO=teamblue DISTRO_TYPE=release make feeds
    ```

* Build specific packages

    ```sh
    MACHINE=gbquad4k DISTRO=teamblue DISTRO_TYPE=release make init

    cd builds/teamblue/release/gb7252/

    source env.source

    bitbake nfs-utils rpcbind ...
    ```





Build Status - branch 7.3:    [![Build Status](https://travis-ci.org/teamblue-e2/enigma2.svg?branch=7.3)](https://travis-ci.org/teamblue-e2/enigma2)

Build Status - branch 7.3:    [![Build Status](https://circleci.com/gh/teamblue-e2/enigma2.svg?style=shield&branch=7.3)]()
