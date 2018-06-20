import os
import hashlib
import json
import attr


@attr.s
class Version(object):
    name = attr.ib()
    path = attr.ib()
    root_path = attr.ib()
    combined_sha = hashlib.sha256()

    def __attrs_post_init__(self):
        self.root = {
            self.name: {
                'items': {}
            }
        }

        for f in [x for x in os.listdir(self.path)
                  if os.path.isfile(os.path.join(self.path, x))]:
            self.root[self.name]['items'].update({
                f: {
                    'sha256':
                        self._sha256_checksum(os.path.join(self.path, f)),
                    'size': os.path.getsize(os.path.join(self.path, f)),
                    'path':
                        os.path.join(self.path.replace(self.root_path, ''), f),
                    'ftype': self._get_type(f)
                }
            })

        if len(self.root[self.name]['items']) > 1 and \
                self.root[self.name]['items'].get('lxd.tar.xz'):
            self.root[self.name]['items']['lxd.tar.xz']['combined_sha256'] = \
                self.combined_sha.hexdigest()

    def _get_type(self, name):
        if 'squashfs' in name:
            return 'squashfs'
        elif 'vcdiff' in name:
            return 'squashfs.vcdiff'
        else:
            return name

    def _sha256_checksum(self, filename, block_size=65536):
        sha256 = hashlib.sha256()
        with open(filename, 'rb') as f:
            for block in iter(lambda: f.read(block_size), b''):
                sha256.update(block)
                self.combined_sha.update(block)
        return sha256.hexdigest()


@attr.s
class Images(object):

    def __attrs_post_init__(self):
        self.root = {
            'format': 'products:1.0',
            'datatype': 'image-downloads',
            'content_id': 'images',
            'products': {}
        }

    def add(self, name, path, root):
        if os.path.exists(path):
            v = Version(path.split('/')[-1], path, root)

            if name not in self.root['products']:
                fields = name.split(':')
                self.root['products'].update({
                    name: {
                        'versions': {},
                        'os': fields[0],
                        'release': fields[1],
                        'release_title': fields[1],
                        'arch': fields[2],
                        'aliases': '/'.join(fields)
                    }
                })

            self.root['products'][name]['versions'].update(v.root)

    def to_json(self):
        return json.dumps(self.root)
