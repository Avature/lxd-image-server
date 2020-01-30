import os
import sys
import re
import traceback
import logging
import queue
import threading
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
import click
import inotify.adapters
from inotify.constants import (IN_ATTRIB, IN_DELETE, IN_MOVED_FROM,
                               IN_MOVED_TO, IN_CLOSE_WRITE)
from lxd_image_server.simplestreams.images import Images
from lxd_image_server.tools.cert import generate_cert
from lxd_image_server.tools.operation import Operations
from lxd_image_server.tools.mirror import MirrorManager
from lxd_image_server.tools.config import Config


logger = logging.getLogger('lxd-image-server')
event_queue = queue.Queue()

def threaded(fn):
    def wrapper(*args, **kwargs):
        threading.Thread(target=fn, args=args, kwargs=kwargs).start()
    return wrapper


def configure_log(log_file, verbose=False):
    filename = log_file

    if log_file == 'STDOUT':
        handler = logging.StreamHandler(sys.stdout)
    elif log_file == 'STDERR':
        handler = logging.StreamHandler(sys.stderr)
    else:
        handler = TimedRotatingFileHandler(
            filename,
            when="d", interval=7, backupCount=4)
    formatter = logging.Formatter('[%(asctime)s] [LxdImgServer] [%(levelname)s] %(message)s')
    handler.setFormatter(formatter)

    logger.setLevel('DEBUG' if verbose else 'INFO')
    logger.addHandler(handler)


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



def config_inotify_setup(skipWatchingNonExistent: bool) -> inotify.adapters.Inotify:
    i = inotify.adapters.Inotify()
    watchedDirs = {}

    for p in Config.paths:
        if os.path.exists(p):
            if os.path.isfile(p):
                logger.debug("Watching existing config file {}".format(p))
                i.add_watch(p, mask= inotify.constants.IN_CLOSE_WRITE | inotify.constants.IN_DELETE)
            else:
                logger.debug("Watching existing config directory {}".format(p))
                i.add_watch(p) # SEEME: all events?
        elif not skipWatchingNonExistent:
            (d, n) = os.path.split(p)
            while not os.path.exists(d):
                (d, n) = os.path.split(d)
            if d not in watchedDirs:
                i.add_watch(d, inotify.constants.IN_DELETE | inotify.constants.IN_CLOSE_WRITE | inotify.constants.IN_CREATE)
                logger.debug("Watching directory {} as base for {}".format(d, p))
                watchedDirs[d] = True

    return i

@threaded
def update_config(skipWatchingNonExistent = True):
    i = config_inotify_setup(skipWatchingNonExistent)
    while True:
        reload = False
        for event in i.event_gen(yield_nones=False):
            (_, mask, dir, file) = event
            fp = os.path.join(dir, file).rstrip(os.path.sep)
            for p in Config.paths:
                if p == fp or (dir == p):
                    reload = True
                    break
            if reload:
                break

        if reload:
            logger.debug("Will reload configuration")
            Config.reload_data()
            i = config_inotify_setup()
            MirrorManager.update_mirror_list()
        else:
            logger.debug("No need to reload configuration")


@threaded
def update_metadata(img_dir, streams_dir):
    MirrorManager.img_dir = img_dir
    MirrorManager.update_mirror_list()
    while True:
        events = event_queue.get()
        ops = Operations(events, str(Path(img_dir).resolve()))
        if ops:
            logger.info('Updating server: %s', ','.join(
                str(x) for x in ops.ops))
            images = Images(str(Path(streams_dir).resolve()), logger=logger)
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
@click.option('--log-file', default='./lxd-image-server.log',
              show_default=True)
@click.option('--verbose', help='Sets log level to debug',
              is_flag=True, default=False)
def cli(log_file, verbose):
    configure_log(log_file, verbose)


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

    img_dir = Path(img_dir).expanduser().resolve()
    streams_dir = Path(streams_dir).expanduser().resolve()

    images = Images(str(Path(streams_dir).resolve()), rebuild=True, logger=logger)

    # Generate a fake event to update all tree
    fake_events = [
        (None, ['IN_ISDIR', 'IN_CREATE'],
            str(img_dir.parent), str(img_dir.name))
    ]
    operations = Operations(fake_events, str(img_dir))
    images.update(operations.ops)
    images.save()

    logger.info('Server updated')


@cli.command()
@click.option('--root_dir', default='/var/www/simplestreams',
              show_default=True)
@click.option('--ssl_dir', default='/etc/nginx/ssl', show_default=True,
              callback=lambda ctx, param, val: Path(val))
@click.option('--ssl_skip', default=False, is_flag=True)
@click.option('--nginx_skip', default=False, is_flag=True)
@click.pass_context
def init(ctx, root_dir, ssl_dir, ssl_skip, nginx_skip):
    root_dir = Path(root_dir).expanduser().resolve()

    if not Path(root_dir).exists():
        logger.error('Root directory does not exists')
    else:
        if nginx_skip:
            ssl_skip = True

        if not ssl_skip:
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

        if not nginx_skip:
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
@click.option('--skip-watch-config-non-existent', default=False, type=bool, is_flag=True)
@click.pass_context
def watch(ctx, img_dir, streams_dir, skip_watch_config_non_existent: bool):
    path_img_dir = str(Path(img_dir).expanduser().resolve())
    path_streams_dir = str(Path(streams_dir).expanduser().resolve())
    logger.info("Starting watch process")

    Config.load_data()
    # Lauch threads
    # SEEME: in case an event will come from watching config files, there is a race condition between update_config
    # thread using indirectly MirrorManager.img_dir and thread update_metadata setting MirrorManager.img_dir
    # Also, race condition on calling MirrorManager.update_mirror_list() in both threads.
    update_config(skip_watch_config_non_existent)
    update_metadata(path_img_dir, path_streams_dir)
    logger.debug("Watching image directory {}".format(path_img_dir))

    i = inotify.adapters.InotifyTree(path_img_dir,
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
