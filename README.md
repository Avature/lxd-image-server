Lxd-image-server
================
[![Build Status](https://travis-ci.org/Avature/lxd-image-server.svg?branch=master)](https://travis-ci.org/Avature/lxd-image-server)

Creates and manages a simplestreams lxd image server on top of nginx.
If installed as a debian package, a new service is created and it monitors
if there are any changes in the image directory and updates json files.

Requirements
------------

* Python: Version 3.5.2 or higher.

* Nginx

* OpenSSL

Building the debian package
---------------------------

### Building the package ###

To build lxd-image-server, first, install the build dependecies:

```bash
# debhelper >= 9
# dh-virtualenv >= 9
apt-get install debhelper dh-exec python3 python-dev dh-virtualenv
```

Then build the package:

```bash
dpkg-buildpackage -us -uc -b
```

### Building the package in a Docker container ###

To build lxd-image-server itself in a Docker container, call docker build:

```bash
docker build --tag lxd-image-server-builder .
```

This will build the DEB package for Ubuntu Bionic by default. Add e.g.
--build-arg distro=ubuntu:xenial to build for Ubuntu Xenial.

The resulting files must be copied out of the build container, using these
commands:

```bash
mkdir -p dist && docker run --rm lxd-image-server-builder tar -C /dpkg -c . | tar -C dist -xv
```

Installation
------------

### From debian package (recommended) ###

The debian package will automatically copy the source files, create the user lxdadm
to upload the files and setup the nginx server with its configuration (included a
self signed ssl certificate).

* **Install from repository**:

```sh
apt-get install lxd-image-server
```

* **Install using dpkg**:

```sh
dpkg -i lxd-image-server_0.0.1~xenial_all.deb
```

After the installation of the package, a rsa key has to be generated at
/home/lxdadm/.ssh to control the upload of images:

```sh
ssh-keygen
Generating public/private rsa key pair.
Enter file in which to save the key (/root/.ssh/id_rsa): # use /home/lxdadm/.ssh/id_rsa
...
```

The generated id_rsa key will be used to upload files to the server.

### From source code ###

Clone the repository and run:

```sh
python setup.py install
```

The subcommand init generates all the default directories, ssl keys and links nginx
configuration (when using default configuration it is recommended to use debian installation)

Usage
-----

The installed service will automatically monitor the image directory and update
all the required metadata. No further commands are needed.

This is the structure the simplestreams server needs to have.

```
- /var/www                                         # document root
        `- simplestreams
           |- images                               # images folder
           |  `- iats                              # environment
           |     `- xenial                         # release
           |        `- amd64                       # architecture
           |           `- default                  # box type
           |              `- 20180716_12:00        # version 1
           |                 |- lxd.tar.xz         # index and templates
           |                 `- rootfs.squashfs    # rootfs of container
           `- streams
              `- v1
                 |- index.json                     # index of products
                 `- images.json                    # info with versions of products
```

The command `lxd-image-server` can be used to manage the server manually:

```sh
Usage: lxd-image-server [OPTIONS] COMMAND [ARGS]...

Options:
  --log-file TEXT  [default: ./lxd-image-server.log]
  --verbose        Sets log level to debug
  --help           Show this message and exit.

Commands:
  init
  update
  watch

Default paths:
    - Index files: /var/www/simplestreams/streams/v1
    - Image dirs: /var/www/simplestreams/images
```

### Subcommands ###

#### init ####

Init creates default configuration needed for the server. See Installation
section for more info.

#### Update ####

Update recreates all the metadata from scratch, and recalculate the
sha256 info for all the images. This option is only intended as a safeguard or in case
the service is not running.

#### Watch ####

Watch will start the monitoring of the directory. It is intended to be
used only if the service is not running.

How to use my new server?
-------------------------

### How to add server as lxd remote ###

Once your own image server is running, you can add it as new remote on lxc:

```bash
lxc remote add <name> <url> --protocol=simplestreams
```

Remember add the certificate:

```bash
openssl s_client -showcerts -connect <url>:443 </dev/null 2>/dev/null | openssl x509 -outform PEM > my-lxd-image-server.cert
cp my-lxc-image-server.cert /user/local/share/ca-certificates
update-ca-certificates
systemctl restart lxd
```

Also, you can use https://letsencrypt.org/ and makes easer use your server.

### Publish a new image ###

Create a image container and publish:

```bash
lxc launch lxc:ubuntu/bionic/amd64 n1
lxc exec n1 -- apt-get -y install vim
lxc stop n1
lxc publish --public n1 --alias=bionic-vim
lxc image copy bionic-vim <url>
```

Now, you can use your image in a new container

```bash
lxc launch bionic-vim ntest
lxc exec ntest -- vim -c "smile"
```
