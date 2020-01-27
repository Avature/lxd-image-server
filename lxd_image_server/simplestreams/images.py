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
        items = {}
        sha256_lxd = None
        lxd_key = None

        # first we build the list of files. No sha256 yet
        for f in Path(self.path).iterdir():
            if not f.is_file() or f.name in ['metadata.json']:
                continue
            data = {
                'size': f.stat().st_size,
                'path':
                    str('images' /
                        f.relative_to(self.root_path)),
                'ftype': self._get_type(f.name)
            }

            if data['ftype'] == 'lxd.tar.xz':
                lxd_key = str(f)
                sha256_lxd = hashlib.sha256()
                self._do_sha256_checksum(str(f), [sha256_lxd])
                data['sha256'] = sha256_lxd.hexdigest()

            items[str(f)] = data

        for (f, data) in items.items():
            if 'sha256' in data:
                continue

            sha_object = hashlib.sha256()
            sha_object2 = None
            lxd_key_additional = None

            if data['ftype'] in ['squashfs', 'root.tar.xz'] and sha256_lxd is not None:
                sha_object2 = sha256_lxd.copy()

            self._do_sha256_checksum(str(f), [sha_object, sha_object2]),
            data['sha256'] = sha_object.hexdigest()
            if sha_object2 is not None:
                if data['ftype'] == 'squashfs':
                    items[lxd_key]['combined_squashfs_sha256'] = sha_object2.hexdigest()
                elif data['ftype'] == 'root.tar.xz':
                    # combined_sha256 is legacy key
                    items[lxd_key]['combined_rootxz_sha256'] = items[lxd_key]['combined_sha256'] = sha_object2.hexdigest()

        for (f, data) in items.items():
            self.root[self.name]['items'].update({ Path(f).name : data })


    def _get_type(self, name):
        if 'squashfs' in name:
            return 'squashfs'
        elif 'vcdiff' in name:
            return 'squashfs.vcdiff'
        return name

    def _do_sha256_checksum(self, filename, sha_objects: list, block_size=65536):
        with open(filename, 'rb') as f:
            for block in iter(lambda: f.read(block_size), b''):
                for sha_object in sha_objects:
                    if sha_object is not None:
                        sha_object.update(block)


@attr.s
class Images(object):
    path = attr.ib(default=None)
    rebuild = attr.ib(default=False)
    logger = attr.ib(default=None)

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

    def _load_info_from_file(self, path):
        f = Path(path, "metadata.json")
        o = {}
        if f.exists() and f.is_file():
            if self.logger:
                self.logger.debug("Loading info from {}".format(str(f)))
            try:
                with open(str(f)) as json_file:
                    o = json.load(json_file)
            except:
                if self.logger:
                    self.logger.warn("Failed to load JSON from {}".format(str(f)))
        return o

    def _add(self, name, path, root):

        if Path(path).exists():
            v = Version(path.split('/')[-1], path, root)

            if name not in self.root['products']:
                fields = name.split(':')

                o = self._load_info_from_file(path)
                alias = '/'.join(fields)
                d = {
                    'versions': {},
                    'os': fields[0],
                    'release': fields[1],
                    'release_title': fields[1],
                    'arch': fields[2],
                    'aliases': alias
                }
                # direct copy fields:
                for field in ['os', 'release_title', 'aliases']:
                    if field in o:
                        d[field] = o[field]

                if alias not in d['aliases'].split(","):
                    d['aliases'] += "," + alias

                self.root['products'].update( { name: d } )

            self.root['products'][name]['versions'].update(v.root)

    def to_json(self):
        return json.dumps(self.root)

    def save(self):
        if self.path:
            with open(str(Path(self.path, 'images.json')), 'w') as outfile:
                self.root['last_update'] = time.time()
                json.dump(self.root, outfile)
        self.index.save()
