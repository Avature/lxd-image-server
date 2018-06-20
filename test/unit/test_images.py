import json
import tempfile
import os
import copy
import shutil
from pathlib import Path
from hamcrest import assert_that, is_, equal_to
from mock import patch
from lxd_image_server.simplestreams.images import Images
from lxd_image_server.tools.operation import OperationType, Operation


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
                                'images/ubuntu/xenial/amd64/default/2018062'
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
                            'path': 'images/ubuntu/xenial/amd64/default/2018'
                                '0620_12:18/lxd.tar.xz'
                        }
                    }
                }
            }
        }
    }
}


EXTRA = {
    '20180620_12:28': {
        'items': {
            'rootfs.squashfs': {
                'sha256':
                    '425ed4e4a36b30ea21b90e21c712c649e82'
                    '14c29b7eaf68089d1039c6e55384c',
                'ftype': 'squashfs',
                'size': 32, 'path':
                    'images/ubuntu/xenial/amd64/default/2018062'
                    '0_12:28/rootfs.squashfs'
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
                'path': 'images/ubuntu/xenial/amd64/default/2018'
                    '0620_12:28/lxd.tar.xz'
            }
        }
    }
}


class TestImages(object):

    def _generate_files(self, version, tmpdir):
        work_dir = os.path.join(tmpdir, 'ubuntu', 'xenial',
                                'amd64', 'default', version)
        os.makedirs(work_dir)
        lxd = open(os.path.join(work_dir, 'lxd.tar.xz'), 'w')
        root = open(os.path.join(work_dir, 'rootfs.squashfs'), 'w')
        lxd.write('AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA')
        root.write('BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB')
        lxd.close()
        root.close()
        return work_dir

    @patch('lxd_image_server.simplestreams.images.Index')
    def test_add_files(self, index_mock):
        with tempfile.TemporaryDirectory() as tmpdir:
            self._generate_files('20180620_12:18', tmpdir)
            extra_dir = self._generate_files('20180620_12:28', tmpdir)
            new_index = copy.deepcopy(INDEX)
            new_index['products']['ubuntu:xenial:amd64:default'][
                'versions'].update(EXTRA)

            with open(str(Path(tmpdir, 'images.json')), 'w') as image_file:
                json.dump(INDEX, image_file)

            images = Images(tmpdir)
            images.update([
                Operation(
                    extra_dir,
                    OperationType.ADD_MOD,
                    tmpdir)
            ])

            assert '20180620_12:28' in images.root['products'][
                'ubuntu:xenial:amd64:default']['versions']
            assert '20180620_12:18' in images.root['products'][
                'ubuntu:xenial:amd64:default']['versions']

    @patch('lxd_image_server.simplestreams.images.Index')
    def test_delete_files(self, mock_index):
        with tempfile.TemporaryDirectory() as tmpdir:
            work_dir = self._generate_files('20180620_12:18', tmpdir)
            new_index = copy.deepcopy(INDEX)
            new_index['products']['ubuntu:xenial:amd64:default'][
                'versions'].update(EXTRA)
            with open(str(Path(tmpdir, 'images.json')), 'w') as image_file:
                json.dump(new_index, image_file)

            images = Images(tmpdir)
            images.update([
                Operation(
                    str(Path(work_dir).parent / '20180620_12:28'),
                    OperationType.ADD_MOD,
                    tmpdir)
            ])
            assert_that(images.root, is_(equal_to(INDEX)))

    @patch('lxd_image_server.simplestreams.images.Index')
    def test_delete_all_files(self, mock_index):
        with tempfile.TemporaryDirectory() as tmpdir:
            work_dir = str(
                Path(tmpdir, 'ubuntu/xenial/amd64/default/20180620_12:18'))
            new_index = copy.deepcopy(INDEX)
            del new_index['products']['ubuntu:xenial:amd64:default']

            with open(str(Path(tmpdir, 'images.json')), 'w') as image_file:
                json.dump(new_index, image_file)

            images = Images(tmpdir)
            images.update([
                Operation(
                    str(Path(work_dir).parent / '20180620_12:18'),
                    OperationType.ADD_MOD,
                    tmpdir)
            ])
            assert_that(images.root, is_(equal_to(new_index)))

    @patch('lxd_image_server.simplestreams.images.Index')
    def test_move_files(self, mock_index):
        with tempfile.TemporaryDirectory() as tmpdir:
            work_dir = self._generate_files('20180620_12:28', tmpdir)

            with open(str(Path(tmpdir, 'images.json')), 'w') as image_file:
                json.dump(INDEX, image_file)

            new_index = copy.deepcopy(INDEX)
            new_index['products']['ubuntu:xenial:amd64:default'][
                'versions'].update(EXTRA)
            del new_index['products']['ubuntu:xenial:amd64:default'][
                'versions']['20180620_12:18']
            images = Images(tmpdir)
            images.update([
                Operation(
                    str(Path(work_dir).parent / '20180620_12:18'),
                    OperationType.DELETE,
                    tmpdir),
                Operation(
                    str(Path(work_dir).parent / '20180620_12:28'),
                    OperationType.ADD_MOD,
                    tmpdir)
            ])
            assert '20180620_12:28' in images.root['products'][
                'ubuntu:xenial:amd64:default']['versions']
            assert '20180620_12:18' not in images.root['products'][
                'ubuntu:xenial:amd64:default']['versions']

    @patch('lxd_image_server.simplestreams.images.Index')
    def test_move_root(self, mock_index):
        with tempfile.TemporaryDirectory() as tmpdir:
            work_dir = self._generate_files('20180620_12:18', tmpdir)
            other_dir = os.path.join(tmpdir, 'ubuntu', 'xenial',
                                     'amd64', 'other')
            shutil.move(str(Path(work_dir).parent), other_dir)

            with open(str(Path(tmpdir, 'images.json')), 'w') as image_file:
                json.dump(INDEX, image_file)

            images = Images(tmpdir)
            images.update([
                Operation(
                    str(Path(other_dir, '20180620_12:18')),
                    OperationType.ADD_MOD,
                    tmpdir),
                Operation(
                    str(Path(work_dir).parent),
                    OperationType.DELETE,
                    tmpdir, True)
            ])
            assert 'ubuntu:xenial:amd64:default' not in images.root['products']
            assert 'ubuntu:xenial:amd64:other' in images.root['products']
