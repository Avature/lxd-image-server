import re
import os
from enum import IntEnum
from pathlib import Path
import attr


def convert_operation(event_types):
    for event in event_types:
        if any(event == x for x in ('IN_CLOSE_WRITE', 'IN_MOVED_TO',
                                    'IN_ATTRIB', 'IN_CREATE')):
            return OperationType.ADD_MOD
        elif event == 'IN_DELETE' or event == 'IN_MOVED_FROM':
            return OperationType.DELETE


class OperationType(IntEnum):
    ADD_MOD = 1
    DELETE = 2


class Operation(object):

    def __init__(self, path, operation, root, is_root=False):
        self.path = path
        self.root = root
        self.is_root = is_root
        if is_root:
            self.name = ':'.join(Path(path).relative_to(root).parts)
        else:
            self.name = ':'.join(Path(path).relative_to(root).parent.parts)
        self.operation = operation if isinstance(operation, OperationType) \
            else convert_operation(operation)

    def __hash__(self):
        return hash((self.path, self.operation))

    def __eq__(self, other):
        if self.path == other.path and self.operation == other.operation:
            return True
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __str__(self):
        return '[ %s, %s ]' % (
            self.path, 'ADD_MOD' if self.operation == OperationType.ADD_MOD
            else 'DELETE')


@attr.s
class Operations(object):
    events = attr.ib()
    root = attr.ib()

    def __attrs_post_init__(self):
        self.ops = set([])
        self._process_events()

    def _process_events(self):
        tmp_ops = set([])
        for event in self.events:

            # Operations done over directories
            _, actions, parent, name = event
            if 'IN_ISDIR' in actions:
                if re.match('\d{8}_\d{2}:\d{2}', name):
                    self.ops.add(
                        Operation(
                            str(Path(parent, name)),
                            actions, self.root))
                else:
                    if 'IN_MOVED_FROM' not in actions:
                        tmp_ops.add(
                            Operation(
                                str(Path(parent, name)),
                                actions, self.root))

                    # Delete operation over non existing path
                    else:
                        self.ops.add(
                            Operation(
                                str(Path(parent, name)),
                                actions, self.root, True))

            # Only generate operation if it is a final path
            elif re.match('\d{8}_\d{2}:\d{2}', parent.split('/')[-1]):

                # Files operations are ADD_MOD unless all files has been
                # deleted
                path = Path(parent)
                if path.exists() and [x for x in path.iterdir()
                                      if x.is_file()]:
                    op = OperationType.ADD_MOD
                else:
                    op = OperationType.DELETE

                self.ops.add(Operation(parent, op, self.root))

        # Generate operations for root paths
        for op in tmp_ops:
            for root, dirs, _ in os.walk(op.path):
                for elem in [x for x in dirs
                             if re.match('\d{8}_\d{2}:\d{2}', x)]:
                    self.ops.add(
                        Operation(
                            str(Path(root, elem)),
                            op.operation, self.root))
