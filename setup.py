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
    license='Apache License 2.0',
    author='Avature',
    author_email='devops@avature.net',
    url='https://github.com/avature/lxd-image-server',
    description='Package to create and manage a simplestreams'
                'lxd image server on top of nginx.',
    long_description=io.open('README.md', encoding='utf8').read(),
    long_description_content_type='text/markdown',
    install_requires=open('requirements.txt').read().splitlines(),
    entry_points={
        'console_scripts': ['lxd-image-server = lxd_image_server.cli:main']
    },
    packages=find_packages(),
    classifiers=[
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: POSIX :: Linux',
        'Topic :: Internet :: WWW/HTTP :: HTTP Servers'
    ]
)
