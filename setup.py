#!/usr/bin/env python

from setuptools import setup

with open('README.md') as readme_file:
    readme = readme_file.read()

with open('VERSION') as f:
    version = f.read().lstrip().rstrip()

setup(
    name='pearback',
    version=version,
    description="module and tool to interact with iOS backups",
    url='https://github.com/mx-pycoder/pearback',
    long_description=readme+"\n\n",
    author="Marnix Kaart",
    author_email='mx@pycoder.nl',
    packages=['pearback'],
    license="MIT license",
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Intended Audience :: End Users/Desktop',
        'Topic :: System :: Archiving :: Backup',
        'Topic :: Utilities',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3 :: Only',
        ],
    keywords='iOS backup Manifest.db Manifest.mbdb',
    entry_points={
        'console_scripts': ['pearback=pearback.cmdline:main'],
        },
    install_requires=[
        'biplist',
        'tqdm'
    ],
    zip_safe=False,
)
