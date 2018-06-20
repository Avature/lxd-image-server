% lxd-image-server(1)

Lxd-image-server
================

Create and manage a simplestreams lxd image server on top of nginx.
If installed as a debian package, a new service is created and it monitors
if there are any changes in the image directory and updates json files.

Default paths:
    - Index files: /var/www/streams/v1
    - Image dirs: /var/www/images


Usage: lxd-image-server [OPTIONS] COMMAND [ARGS]...

Options:
  --help  Show this message and exit.

Commands:
  init
  update
  watch