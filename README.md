% lxd-image-server(1)

Lxd-image-server
================

Creates and manages a simplestreams lxd image server on top of nginx.
If installed as a debian package, a new service is created and it monitors
if there are any changes in the image directory and updates json files.

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

Subcommand init creates default configuration needed for the server. See Installation
section for more info.

Subcommand update recreates all the metadata from scratch, and recalculate the
sha256 info for all the images. This option is only intended as a safeguard or in case
the service is not running.

Subcommand watch will start the monitoring of the directory. It is intended to be 
used only if the service is not running.

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

Requirements
------------

* Python: Version 3.5.2 or higher.

* Nginx

* OpenSSL