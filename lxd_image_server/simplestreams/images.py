import hashlib
import json
import time
from pathlib import Path
import attr
from lxd_image_server.tools.operation import OperationType
from lxd_image_server.simplestreams.index import Index


@attr.s
class Version(object):
    name = attr.ib()
    path = attr.ib()
    root_path = attr.ib()

    def __attrs_post_init__(self):
        self.root = {
            self.name: {
                'items': {}
            }
        }
        self.combined_sha = hashlib.new('sha256')

        for f in [str(x.name) for x in Path(self.path).iterdir()
                  if Path(self.path, x).is_file()]:
            self.root[self.name]['items'].update({
                f: {
                    'sha256':
                        self._sha256_checksum(str(Path(self.path, f))),
                    'size': Path(self.path, f).stat().st_size,
                    'path':
                        str('images' /
                            Path(self.path).relative_to(self.root_path) / f),
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
    path = attr.ib(default=None)
    rebuild = attr.ib(default=False)

    def __attrs_post_init__(self):
        self.index = Index(self.path, self.rebuild)
        if not self.path or not Path(self.path).exists() or self.rebuild:
            self.root = {
                'format': 'products:1.0',
                'datatype': 'image-downloads',
                'content_id': 'images',
                'products': {}
            }
        else:
            with open(str(Path(self.path, 'images.json'))) as json_file:
                self.root = json.load(json_file)

    def update(self, operations):
        for op in operations:
            if op.is_root:
                for product in [x for x in self.root['products']
                                if op.name in x]:
                    del self.root['products'][product]
            else:
                # Always delete for the operations and add if needed
                if op.name in self.root['products'] and \
                    op.path.split('/')[-1] in \
                        self.root['products'][op.name]['versions']:
                    del self.root['products'][op.name]['versions'][
                        op.path.split('/')[-1]
                    ]
                    if not self.root['products'][op.name]['versions']:
                        del self.root['products'][op.name]
                        self.index.delete(op.name)

                if op.operation == OperationType.ADD_MOD:
                    self._add(op.name, op.path, op.root)
                    self.index.add(op.name)

    def _add(self, name, path, root):
        if Path(path).exists():
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

    def save(self):
        if self.path:
            with open(str(Path(self.path, 'images.json')), 'w') as outfile:
                self.root['last_update'] = time.time()
                json.dump(self.root, outfile)
        self.index.save()
