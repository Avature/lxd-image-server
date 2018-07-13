import os
import sys
import re
import traceback
import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
import click
import inotify.adapters
from inotify.constants import (IN_ATTRIB, IN_DELETE, IN_MOVED_FROM,
                               IN_MOVED_TO, IN_CLOSE_WRITE)
from lxd_image_server.simplestreams.images import Images
from lxd_image_server.tools.cert import generate_cert
from lxd_image_server.tools.operation import Operations


logger = logging.getLogger('lxd-image-server')


def configure_log(verbose=False):
    filename = '/var/log/lxd-image-server/lxd-image-server.log'

    handler = TimedRotatingFileHandler(
        filename,
        when="d", interval=7, backupCount=4)
    formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s')
    handler.setFormatter(formatter)

    logger.setLevel('DEBUG' if verbose else 'INFO')
    logger.addHandler(handler)


def needs_update(events):
    needs_upd = False
    modified_files = []
    for event in list(events):
        if re.match('\d{8}_\d{2}:\d{2}', event[3]) or \
            any(k in event[1]
                for k in ('IN_MOVED_FROM', 'IN_MOVED_TO',
                          'IN_DELETE', 'IN_CLOSE_WRITE')):
            logger.debug('Event: PATH=[{}] FILENAME=[{}] EVENT_TYPES={}'
                         .format(event[2], event[3], event[1]))
            modified_files.append(event)
            needs_upd = True

    return needs_upd, modified_files


def fix_permissions(path):
    Path(path).chmod(0o777)
    for root, dirs, files in os.walk(path):
        for elem in files:
            Path(root, elem).chmod(0o777)
        for elem in dirs:
            Path(root, elem).chmod(0o777)


@click.group()
@click.option('--verbose', help='Sets log level to debug',
              is_flag=True, default=False)
def cli(verbose):
    configure_log(verbose)


@cli.command()
@click.argument('img_dir', default='/var/www/images')
@click.argument('streams_dir', default='/var/www/streams/v1')
@click.pass_context
def update(ctx, img_dir, streams_dir):
    logger.info('Updating server')

    img_dir = img_dir.rstrip()
    images = Images(streams_dir, rebuild=True)

    # Generate a fake event to update all tree
    fake_events = [
        (None, ['IN_ISDIR', 'IN_CREATE'],
            str(Path(img_dir).parent), str(Path(img_dir).name))
    ]
    operations = Operations(fake_events, str(img_dir))
    images.update(operations.ops)
    images.save()

    logger.info('Server updated')


@cli.command()
@click.argument('root_dir', default='/var/www')
@click.argument('ssl_dir', default='/etc/nginx/ssl')
@click.pass_context
def init(ctx, root_dir, ssl_dir):
    if not Path(root_dir).exists():
        logger.error('Root directory does not exists')
    else:
        if not Path(ssl_dir).exists():
            os.makedirs(ssl_dir)

        if not Path(ssl_dir, 'nginx.key').exists():
            generate_cert(ssl_dir)

        img_dir = str(Path(root_dir, 'images'))
        streams_dir = str(Path(root_dir, 'streams/v1'))
        if not Path(img_dir).exists():
            os.makedirs(img_dir)
        if not Path(streams_dir).exists():
            os.makedirs(streams_dir)
        conf_path = Path('/etc/nginx/sites-enabled/simplestreams.conf')
        if not conf_path.exists():
            conf_path.symlink_to('/etc/nginx/sites-enabled/simplestreams.conf')
            os.system('nginx -s reload')

        if not Path(root_dir, 'streams', 'v1', 'images.json').exists():
            ctx.invoke(update, img_dir=str(Path(root_dir, 'images')),
                       streams_dir=str(Path(root_dir, 'streams', 'v1')))

        fix_permissions(img_dir)
        fix_permissions(streams_dir)


@cli.command()
@click.argument('img_dir', default='/var/www/images')
@click.argument('streams_dir', default='/var/www/streams/v1')
@click.pass_context
def watch(ctx, img_dir, streams_dir):
    img_dir = img_dir.rstrip()
    i = inotify.adapters.InotifyTree(img_dir,
                                     mask=(IN_ATTRIB | IN_DELETE |
                                           IN_MOVED_FROM | IN_MOVED_TO |
                                           IN_CLOSE_WRITE))

    while True:
        events = i.event_gen(yield_nones=False, timeout_s=15)
        needs_upd, files_changed = needs_update(events)
        if needs_upd:
            ops = Operations(files_changed, img_dir)
            logger.info('Updating server:\n\t\t%s', '\n\t\t'.join(
                str(x) for x in ops.ops))
            images = Images(streams_dir)
            images.update(ops.ops)
            images.save()
            logger.info('Server updated')


def main():
    try:
        sys.exit(cli())
    except Exception:
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == '__main__':
    main()
