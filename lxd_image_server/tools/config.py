import os
from pathlib import Path
from pkg_resources import resource_filename
from threading import Lock

import confight


class Config():

    _lock = Lock()
    pidfile = Path('/var/run/lxd-image-server/pidfile')
    data = {}

    @classmethod
    def load_data(cls):
        default = resource_filename("lxd_image_server", "default_config.toml")
        paths = [os.getenv("LXD_IMAGE_SERVER_CONFIG")]
        with cls._lock:
            cls.data = confight.load_app(
                'lxd-image-server',
                default=default,
                paths=paths
            )

    @classmethod
    def get(cls, key, default=None):
        with cls._lock:
            return cls.data.get(key, default)

