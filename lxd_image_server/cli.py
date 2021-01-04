import os
import sys
import re
import traceback
import logging
import queue
import signal
import threading
from logging.config import dictConfig
from pathlib import Path
import click
import inotify.adapters
import pidfile
from inotify.constants import (IN_ATTRIB, IN_DELETE, IN_MOVED_FROM,
                               IN_MOVED_TO, IN_CLOSE_WRITE)
from lxd_image_server.simplestreams.images import Images
from lxd_image_server.tools.cert import generate_cert
from lxd_image_server.tools.operation import Operations
from lxd_image_server.tools.mirror import MirrorManager
from lxd_image_server.tools.config import Config


logger = logging.getLogger(__name__)
event_queue = queue.Queue()


def threaded(fn):
    def wrapper(*args, **kwargs):
        threading.Thread(target=fn, args=args, kwargs=kwargs).start()
    return wrapper


def configure_log(verbose=False):
    log_config = Config.get('logging', {})
    if verbose:
        for ltype in ['handlers', 'loggers']:
            for elem in log_config.get(ltype, []):
                elem.setLeve('DEBUG')
    dictConfig(log_config)


def needs_update(events):
    modified_files = []
    for event in list(events):
        if re.match('\d{8}_\d{2}:\d{2}', event[3]) or \
            any(k in event[1]
                for k in ('IN_MOVED_FROM', 'IN_MOVED_TO',
                          'IN_DELETE', 'IN_CLOSE_WRITE')):
            logger.debug('Event: PATH=[{}] FILENAME=[{}] EVENT_TYPES={}'
                         .format(event[2], event[3], event[1]))
            modified_files.append(event)

    return modified_files


def update_config():
    def reload_on_signal(signum, frame):
        logger.info('Relading configuration')
        Config.load_data()
        configure_log()
        MirrorManager.update_mirror_list()
    signal.signal(signal.SIGHUP, reload_on_signal)


@threaded
def update_metadata(img_dir, streams_dir):
    logger.info('start watching for new images')
    MirrorManager.img_dir = img_dir
    MirrorManager.update_mirror_list()
    while True:
        events = event_queue.get()
        ops = Operations(events, str(Path(img_dir).resolve()))
        if ops:
            logger.info('Updating server: %s', ','.join(
                str(x) for x in ops.ops))
            images = Images(str(Path(streams_dir).resolve()))
            images.update(ops.ops)
            images.save()
            MirrorManager.update()
            logger.info('Server updated')


def fix_permissions(path):
    Path(path).chmod(0o775)
    for root, dirs, files in os.walk(path):
        for elem in files:
            Path(root, elem).chmod(0o775)
        for elem in dirs:
            Path(root, elem).chmod(0o775)


@click.group()
@click.option('--verbose', help='Sets log level to debug',
              is_flag=True, default=False)
def cli(verbose):
    Config.load_data()
    configure_log(verbose)


@cli.command()
@click.option('--img_dir', default='/var/www/simplestreams/images',
              show_default=True,
              type=click.Path(exists=True, file_okay=False,
                              resolve_path=True),
              callback=lambda ctx, param, val: Path(val))
@click.option('--streams_dir', default='/var/www/simplestreams/streams/v1',
              show_default=True,
              type=click.Path(exists=True, file_okay=False,
                              resolve_path=True))
@click.pass_context
def update(ctx, img_dir, streams_dir):
    logger.info('Updating server')

    images = Images(str(Path(streams_dir).resolve()), rebuild=True)

    # Generate a fake event to update all tree
    fake_events = [
        (None, ['IN_ISDIR', 'IN_CREATE'],
            str(img_dir.parent), str(img_dir.name))
    ]
    operations = Operations(fake_events, str(img_dir))
    images.update(operations.ops)
    images.save()

    logger.info('Server updated')


@cli.command('reload', help='Reload daemon configuration')
def reload_config():
    pidfile = Config.pidfile
    if pidfile and pidfile.exists():
        with open(pidfile, 'r') as fread:
            pid = int(fread.read())
            logger.warning('Sending SIGHUP to %s for reloading', pid)
            os.kill(pid, signal.SIGHUP)
        return
    logger.warning('pidfile %s does not exist maybe the daemon is not running')


@cli.command()
@click.option('--root_dir', default='/var/www/simplestreams',
              show_default=True)
@click.option('--ssl_dir', default='/etc/nginx/ssl', show_default=True,
              callback=lambda ctx, param, val: Path(val))
@click.pass_context
def init(ctx, root_dir, ssl_dir):
    if not Path(root_dir).exists():
        logger.error('Root directory does not exists')
    else:
        if not ssl_dir.exists():
            os.makedirs(str(ssl_dir))

        if not (ssl_dir / 'nginx.key').exists():
            generate_cert(str(ssl_dir))

        img_dir = str(Path(root_dir, 'images'))
        streams_dir = str(Path(root_dir, 'streams/v1'))
        if not Path(img_dir).exists():
            os.makedirs(img_dir)
        if not Path(streams_dir).exists():
            os.makedirs(streams_dir)
        conf_path = Path('/etc/nginx/sites-enabled/simplestreams.conf')
        if not conf_path.exists():
            conf_path.symlink_to(
                '/etc/nginx/sites-available/simplestreams.conf')
            os.system('nginx -s reload')

        if not Path(root_dir, 'streams', 'v1', 'images.json').exists():
            ctx.invoke(update, img_dir=Path(root_dir, 'images'),
                       streams_dir=Path(root_dir, 'streams', 'v1'))

        fix_permissions(img_dir)
        fix_permissions(streams_dir)


@cli.command()
@click.option('--img_dir', default='/var/www/simplestreams/images',
              show_default=True,
              type=click.Path(exists=True, file_okay=False,
                              resolve_path=True))
@click.option('--streams_dir', default='/var/www/simplestreams/streams/v1',
              type=click.Path(exists=True, file_okay=False,
                              resolve_path=True), show_default=True)
@click.pass_context
def watch(ctx, img_dir, streams_dir):
    with pidfile.PIDFile(Config.pidfile):
        _watch(img_dir, streams_dir)

def _watch(img_dir, streams_dir):
    # Lauch threads
    update_config()
    update_metadata(img_dir, streams_dir)

    i = inotify.adapters.InotifyTree(str(Path(img_dir).resolve()),
                                     mask=(IN_ATTRIB | IN_DELETE |
                                           IN_MOVED_FROM | IN_MOVED_TO |
                                           IN_CLOSE_WRITE))

    while True:
        events = i.event_gen(yield_nones=False, timeout_s=15)
        files_changed = needs_update(events)
        if files_changed:
            event_queue.put(files_changed)


def main():
    try:
        sys.exit(cli())
    except Exception:
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == '__main__':
    main()
