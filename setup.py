#! /usr/bin/env python
import io
import re
from setuptools import setup, find_packages


def get_version_from_debian_changelog():
    with io.open('debian/changelog', encoding='utf8') as stream:
        return re.search(r'\((.+)\)', next(stream)).group(1)


setup(
    name='lxd-image-server',
    version=get_version_from_debian_changelog(),
    author='David Burgos',
    author_email='david.burgos@avature.net',
    url='https://gitlab.xcade.net/david.burgos/lxd-image-server',
    description='Package to create and manage a simplestreams'
                'lxd image server on top of nginx.',
    install_requires=open('requirements.txt').read().splitlines(),
    license='Propietary',
    entry_points={
        'console_scripts': ['lxd-image-server = lxd_image_server.cli:main']
    },
    packages=find_packages(),
    classifiers=[
        'Intended Audience :: Developers',
        'Intended Audience :: QAs',
        'Topic :: Software Development',
        'Topic :: Software Testing'
    ]
)
