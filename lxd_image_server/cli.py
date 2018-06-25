import os
import stat
import sys
import re
import traceback
import logging
import click
from lxd_image_server.simplestreams.index import Index
from lxd_image_server.simplestreams.images import Images
import inotify.adapters
from inotify.constants import IN_ATTRIB, IN_DELETE, IN_MOVED_FROM, IN_MOVED_TO
from lxd_image_server.tools.cert import generate_cert


logging.basicConfig(
    filename='/var/log/lxd-image-server/lxd-image-server.log',
    level=getattr(logging, 'INFO'),
    format='[%(asctime)s] [%(levelname)s] %(message)s'
)
logger = logging.getLogger('lxd-image-server')


def needs_update(events):
    for event in list(events):
        if re.match('\d{8}_\d{2}:\d{2}', event[3]) or \
            any(k in event[1]
                for k in ('IN_MOVED_FROM', 'IN_MOVED_TO', 'IN_DELETE')):
            logger.info('Event: PATH=[{}] FILENAME=[{}] EVENT_TYPES={}'
                        .format(event[2], event[3], event[1]))
            return True
    return False

def fix_permissions(path):
    os.chmod(path, 0o777)
    for root, dirs, files in os.walk(path):
        for elem in files:
            os.chmod(os.path.join(root, elem), 0o777)
        for elem in dirs:
            os.chmod(os.path.join(root, elem), 0o777)

@click.group()
def cli():
    pass


@cli.command()
@click.argument('img_dir', nargs=1, default='/var/www/images')
@click.argument('streams_dir', nargs=1, default='/var/www/streams/v1')
@click.pass_context
def update(ctx, img_dir, streams_dir):
    index = Index()
    images = Images()

    if img_dir[-1] == '/':
        img_dir = img_dir[:-1]

    for root, dirs, _ in os.walk(img_dir):
        for elem in [x for x in dirs if re.match('\d{8}_\d{2}:\d{2}', x)]:
            path = os.path.join(root, elem)
            name = ':'.join(path.replace(img_dir + '/', '').split('/')[:-1])
            index.add(name)
            images.add(name, path, '/'.join(img_dir.split('/')[:-1]))

    index_file = open(os.path.join(streams_dir, 'index.json'), 'w')
    images_file = open(os.path.join(streams_dir, 'images.json'), 'w')
    index_file.write(index.to_json())
    images_file.write(images.to_json())


@cli.command()
@click.argument('root_dir', nargs=1, default='/var/www')
@click.argument('ssl_dir', nargs=1, default='/etc/nginx/ssl')
@click.pass_context
def init(ctx, root_dir, ssl_dir):
    if not os.path.exists(root_dir):
        logger.error('Root directory does not exists')
    else:
        if not os.path.exists(ssl_dir):
            os.makedirs(ssl_dir)

        generate_cert(ssl_dir)

        img_dir = os.path.join(root_dir, 'images')
        streams_dir = os.path.join(root_dir, 'streams/v1')
        if not os.path.exists(img_dir):
            os.makedirs(img_dir)
        if not os.path.exists(streams_dir):
            os.makedirs(streams_dir)

        os.symlink('/etc/nginx/sites-available/simplestreams.conf',
                   '/etc/nginx/sites-enabled/simplestreams.conf')
        os.system('nginx -s reload')

        ctx.invoke(update, img_dir=os.path.join(root_dir, 'images'),
                   streams_dir=os.path.join(root_dir, 'streams', 'v1'))

        fix_permissions(img_dir)
        fix_permissions(streams_dir)


@cli.command()
@click.argument('img_dir', nargs=1, default='/var/www/images')
@click.argument('streams_dir', nargs=1, default='/var/www/streams/v1')
@click.pass_context
def watch(ctx, img_dir, streams_dir):
    i = inotify.adapters.InotifyTree(img_dir,
                                     mask=(IN_ATTRIB | IN_DELETE |
                                           IN_MOVED_FROM | IN_MOVED_TO))

    while True:
        events = i.event_gen(yield_nones=False, timeout_s=15)
        if needs_update(events):
            logger.info('Updating server')
            ctx.forward(update)


def main():
    try:
        sys.exit(cli())
    except Exception:
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == '__main__':
    main()
