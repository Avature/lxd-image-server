import json
import tempfile
import os
from hamcrest import assert_that, is_, equal_to
from lxd_image_server.simplestreams.images import Images


class TestImages(object):

    def test_generate_dir(self):
        INDEX = {
            'content_id': 'images',
            'datatype': 'image-downloads',
            'format': 'products:1.0',
            'products': {
                'ubuntu:xenial:amd64:default': {
                    'arch': 'amd64',
                    'os': 'ubuntu',
                    'release': 'xenial',
                    'release_title': 'xenial',
                    'aliases': 'ubuntu/xenial/amd64/default',
                    'versions': {
                        '20180620_12:18': {
                            'items': {
                                'rootfs.squashfs': {
                                    'sha256':
                                        '425ed4e4a36b30ea21b90e21c712c649e82'
                                        '14c29b7eaf68089d1039c6e55384c',
                                    'ftype': 'squashfs',
                                    'size': 32, 'path':
                                        '/ubuntu/xenial/amd64/default/2018062'
                                        '0_12:18/rootfs.squashfs'
                                },
                                'lxd.tar.xz': {
                                    'sha256':
                                        '55ee740f58335c97d42c32125218eb7c325f'
                                        'be34206912f1aa7af7fd6580c9a1',
                                    'ftype': 'lxd.tar.xz',
                                    'size': 31,
                                    'combined_sha256':
                                        'f3cb81db18dfc60c9ce1ffc07b5614549dc22'
                                        '22890254ba4ccf2469f58e57a5d',
                                    'path': '/ubuntu/xenial/amd64/default/2018'
                                        '0620_12:18/lxd.tar.xz'
                                }
                            }
                        }
                    }
                }
            }
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            version = '20180620_12:18'
            work_dir = os.path.join(tmpdir, 'ubuntu', 'xenial',
                                    'amd64', 'default', version)
            os.makedirs(work_dir)
            lxd = open(os.path.join(work_dir, 'lxd.tar.xz'), 'w')
            root = open(os.path.join(work_dir, 'rootfs.squashfs'), 'w')
            lxd.write('AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA')
            root.write('BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB')
            lxd.close()
            root.close()
            name = ':'.join(work_dir.replace(tmpdir + '/', '').split('/')[:-1])
            images = Images()
            images.add(name, work_dir, tmpdir)
            out = json.loads(images.to_json())
            assert_that(out, is_(equal_to(INDEX)))
