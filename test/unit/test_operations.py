import os
import tempfile
from pathlib import Path
from lxd_image_server.tools.operation import (Operations, Operation,
                                              OperationType)


class TestOperations(object):

    def test_add_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            path = str(
                Path(tmpdir, 'iats/xenial/amd64/default/20180710_12:00'))
            os.makedirs(path)
            Path(path, 'lxd.tar.xz').touch()
            Path(path, 'rootfs.squashfs').touch()
            events = [
                (None, ['IN_ISDIR', 'IN_CREATE'], str(Path(path).parent),
                    '20180710_12:00'),
                (None, ['IN_CLOSE_WRITE'], path, 'lxd.tar.xz'),
                (None, ['IN_CLOSE_WRITE'], path, 'rootfs.squashfs')
            ]
            operations = Operations(events, tmpdir)
            assert len(operations.ops) == 1
            assert any(
                Operation(path, OperationType.ADD_MOD, tmpdir) == k
                for k in operations.ops)

    def test_add_root(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            path = str(
                Path(tmpdir, 'iats/xenial/amd64/default/20180710_12:00'))
            os.makedirs(path)
            Path(path, 'lxd.tar.xz').touch()
            Path(path, 'rootfs.squashfs').touch()
            events = [
                (None, ['IN_CLOSE_WRITE'], path, 'lxd.tar.xz'),
                (None, ['IN_CLOSE_WRITE'], path, 'rootfs.squashfs'),
                (None, ['IN_ISDIR', 'IN_ATTRIB'], str(Path(path).parent),
                    '20180710_12:00'),
                (None, ['IN_ISDIR', 'IN_ATTRIB'],
                    str(Path(path).parent.parent), 'default')
            ]
            operations = Operations(events, tmpdir)
            assert len(operations.ops) == 1
            assert any(
                Operation(path, OperationType.ADD_MOD, tmpdir) == k
                for k in operations.ops)

    def test_add_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            path = str(
                Path(tmpdir, 'iats/xenial/amd64/default'))
            os.makedirs(path)
            Path(path, 'lxd.tar.xz').touch()
            Path(path, 'rootfs.squashfs').touch()
            events = [
                (None, ['IN_ISDIR', 'IN_ATTRIB'],
                    str(Path(path).parent), 'default')
            ]
            operations = Operations(events, tmpdir)
            assert len(operations.ops) == 0

    def test_add_all(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            path = str(
                Path(tmpdir, 'iats/xenial/amd64/default/20180710_12:00'))
            os.makedirs(path)
            Path(path, 'lxd.tar.xz').touch()
            Path(path, 'rootfs.squashfs').touch()
            events = [
                (None, ['IN_ISDIR', 'IN_CREATE'],
                    '/tmp', str(Path(tmpdir).name))
            ]
            operations = Operations(events, '/tmp')
            assert len(operations.ops) == 1
            assert any(
                Operation(path, OperationType.ADD_MOD, tmpdir) == k
                for k in operations.ops)

    def test_remove_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            path = str(
                Path(tmpdir, 'iats/xenial/amd64/default'))
            os.makedirs(path)
            events = [
                (None, ['IN_DELETE'], path + '/20180710_12:00', 'lxd.tar.xz'),
                (None, ['IN_DELETE'], path + '/20180710_12:00',
                    'rootfs.squashfs'),
                (None, ['IN_ISDIR', 'IN_DELETE'], path, '20180710_12:00')
            ]
            operations = Operations(events, tmpdir)
            assert len(operations.ops) == 1
            assert any(
                Operation(path + '/20180710_12:00',
                          OperationType.DELETE, tmpdir) == k
                for k in operations.ops)

    def test_remove_only_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            path = str(
                Path(tmpdir, 'iats/xenial/amd64/default'))
            os.makedirs(path)
            events = [
                (None, ['IN_DELETE'], path + '/20180710_12:00', 'lxd.tar.xz'),
                (None, ['IN_DELETE'], path + '/20180710_12:00',
                    'rootfs.squashfs')
            ]
            operations = Operations(events, tmpdir)
            assert len(operations.ops) == 1
            assert any(
                Operation(path + '/20180710_12:00',
                          OperationType.DELETE, tmpdir) == k
                for k in operations.ops)

    def test_delete_one_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            path = str(
                Path(tmpdir, 'iats/xenial/amd64/default/20180710_12:00'))
            os.makedirs(path)
            Path(path, 'lxd.tar.xz').touch()
            events = [
                (None, ['IN_DELETE'], path, 'rootfs.squashfs'),
            ]
            operations = Operations(events, tmpdir)
            assert len(operations.ops) == 1
            assert any(
                Operation(path, OperationType.ADD_MOD, tmpdir) == k
                for k in operations.ops)

    def test_delete_root(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            path = str(
                Path(tmpdir, 'iats/xenial/amd64/default/20180710_12:00'))
            events = [
                (None, ['IN_DELETE'], path, 'lxd.tar.xz'),
                (None, ['IN_DELETE'], path, 'rootfs.squashfs'),
                (None, ['IN_ISDIR', 'IN_DELETE'], str(Path(path).parent),
                    '20180710_12:00'),
                (None, ['IN_ISDIR', 'IN_DELETE'],
                    str(Path(path).parent.parent), 'default')
            ]
            operations = Operations(events, tmpdir)
            assert len(operations.ops) == 1
            assert any(
                Operation(path, OperationType.DELETE, tmpdir) == k
                for k in operations.ops)

    def test_remove_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            path = str(
                Path(tmpdir, 'iats/xenial/amd64/default'))
            os.makedirs(path)
            Path(path, 'lxd.tar.xz').touch()
            Path(path, 'rootfs.squashfs').touch()
            events = [
                (None, ['IN_ISDIR', 'IN_DELETE'],
                    str(Path(path).parent.parent), 'default')
            ]
            operations = Operations(events, tmpdir)
            assert len(operations.ops) == 0

    def test_move_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            path = str(
                Path(tmpdir, 'iats/xenial/amd64/default/20180710_12:00'))
            other_path = str(
                Path(tmpdir, 'iats/xenial/amd64/other/20180710_12:00'))
            os.makedirs(other_path)
            Path(other_path, 'lxd.tar.xz').touch()
            Path(other_path, 'rootfs.squashfs').touch()
            events = [
                (None, ['IN_ISDIR', 'IN_MOVED_FROM'], str(Path(path).parent),
                    '20180710_12:00'),
                (None, ['IN_ISDIR', 'IN_MOVED_TO'],
                    str(Path(other_path).parent), '20180710_12:00')
            ]
            operations = Operations(events, tmpdir)

            assert len(operations.ops) == 2
            assert any(Operation(path, OperationType.DELETE, tmpdir) == k
                       for k in operations.ops)
            assert any(
                Operation(other_path, OperationType.ADD_MOD, tmpdir) == k
                for k in operations.ops)

    def test_move_root(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            path = str(
                Path(tmpdir, 'iats/xenial/amd64/default'))
            other_path = str(
                Path(tmpdir, 'iats/xenial/amd64/other/20180710_12:00'))
            os.makedirs(other_path)
            Path(other_path, 'lxd.tar.xz').touch()
            Path(other_path, 'rootfs.squashfs').touch()
            events = [
                (None, ['IN_ISDIR', 'IN_MOVED_FROM'],
                    str(Path(path).parent), 'default'),
                (None, ['IN_ISDIR', 'IN_MOVED_TO'],
                    str(Path(other_path).parent.parent), 'other')
            ]
            operations = Operations(events, tmpdir)
            assert len(operations.ops) == 2
            assert any(Operation(path, OperationType.DELETE, tmpdir) == k
                       for k in operations.ops)
            assert any(
                Operation(other_path, OperationType.ADD_MOD, tmpdir) == k
                for k in operations.ops)

    def test_move_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            path = str(
                Path(tmpdir, 'iats/xenial/amd64/default'))
            other_path = str(
                Path(tmpdir, 'iats/xenial/amd64/other'))
            os.makedirs(other_path)
            events = [
                (None, ['IN_ISDIR', 'IN_MOVED_FROM'],
                    str(Path(path).parent), 'default'),
                (None, ['IN_ISDIR', 'IN_MOVED_TO'],
                    str(Path(other_path).parent), 'other')
            ]
            operations = Operations(events, tmpdir)
            assert len(operations.ops) == 1
            assert any(Operation(path, OperationType.DELETE, tmpdir) == k
                       for k in operations.ops)

    def test_move_one_file_from(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            path = str(
                Path(tmpdir, 'iats/xenial/amd64/default/20180710_12:00'))
            os.makedirs(path)
            Path(path, 'lxd.tar.xz').touch()
            events = [
                (None, ['IN_MOVED_FROM'], path, 'rootfs.squashfs'),
            ]
            operations = Operations(events, tmpdir)
            assert len(operations.ops) == 1
            assert any(
                Operation(path, OperationType.ADD_MOD, tmpdir) == k
                for k in operations.ops)

    def test_move_one_file_to(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            path = str(
                Path(tmpdir, 'iats/xenial/amd64/default/20180710_12:00'))
            os.makedirs(path)
            Path(path, 'lxd.tar.xz').touch()
            Path(path, 'rootfs.squashfs').touch()
            events = [
                (None, ['IN_MOVED_TO'], path, 'rootfs.squashfs'),
            ]
            operations = Operations(events, tmpdir)
            assert len(operations.ops) == 1
            assert any(
                Operation(path, OperationType.ADD_MOD, tmpdir) == k
                for k in operations.ops)
