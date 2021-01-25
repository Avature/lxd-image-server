import re
import logging
import subprocess
from threading import Lock
from pathlib import Path
import attr
from lxd_image_server.tools.config import Config


logger = logging.getLogger(__name__)


@attr.s
class Mirror():
    name = attr.ib()
    user = attr.ib()
    key_path = attr.ib()
    url = attr.ib()
    remote = attr.ib()
    img_dir = attr.ib()

    def __attrs_post_init__(self):
        self.root = {}

    def update(self):
        self._sync_path(self.img_dir)

    def _sync_path(self, op_path):
        command = ['rsync', '-azh', '-e', '/usr/bin/ssh -i ' + self.key_path +
                   ' -l ' + self.user, op_path,
                   self.servername + ':' + str(Path(op_path).parent),
                   '--delete']
        logger.debug('running: %s', command)
        try:
            subprocess.run(command).check_returncode()
        except subprocess.CalledProcessError as error:
            logger.error('Fail to synchronize: %s', error)
        else:
            logger.info("Path %s synced for mirror %s", op_path, self.name)

    @property
    def servername(self):
        if self.remote:
            return self.remote
        match = re.search(r'https://([\w\.]*):?\d*', self.url)
        if match:
            return match.group(1)
        else:
            logger.error('Server %s has no host' % self.url)


class MirrorManager():
    img_dir = '/var/www/simplestreams/images'
    mirrors = {}
    _lock = Lock()

    @classmethod
    def update(cls):
        logger.info('Updating all mirrors')
        mirrors = {}
        with cls._lock:
            mirrors = cls.mirrors.copy()
        for _, mirror in cls.mirrors.items():
            mirror.update()

    @classmethod
    def update_mirror_list(cls):
        with cls._lock:
            for name, mirror in Config.get('mirrors', {}).items():
                cls.mirrors[name] = Mirror(
                    name,
                    mirror['user'],
                    mirror['key_path'],
                    mirror['url'],
                    mirror.get('remote'),
                    cls.img_dir
                )
            logger.info('Mirror list updated')
        cls.update()
