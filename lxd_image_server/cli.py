import os
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
    filename='/var/log/lxd-image-server.log',
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


@click.group()
def cli():
    pass


@cli.command()
@click.argument('img_dir', nargs=1, default='/var/www/images')
@click.argument('streams_dir', nargs=1, default='/var/www/streams/v1')
def update(img_dir, streams_dir):
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
        generate_cert(ssl_dir)
        if not os.path.exists(os.path.join(root_dir, 'images')):
            os.makedirs(os.path.join(root_dir, 'images'))
        if not os.path.exists(os.path.join(root_dir, 'streams/v1')):
            os.makedirs(os.path.join(root_dir, 'streams/v1'))

    ctx.invoke(update, os.path.join(root_dir, 'images'),
               os.path.join(root_dir, 'streams', 'v1'))


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
        click.echo(traceback.format_exc())
        sys.exit(1)


if __name__ == '__main__':
    main()
