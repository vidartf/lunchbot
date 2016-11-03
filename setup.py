#!/usr/bin/env python
# coding: utf-8

# the name of the project
name = 'lunchbot'

import sys
from setuptools import setup


setup_args = dict(
    name            = name,
    description     = "Diff and merge of Jupyter Notebooks",
    version         = "1.0.0",
    packages        = ['lunchbot'],
    author          = 'Jupyter Development Team',
    author_email    = 'jupyter@googlegroups.com',
    url             = 'http://jupyter.org',
    license         = 'BSD',
    platforms       = "Linux, Mac OS X, Windows",
    keywords        = ['Interactive', 'Interpreter', 'Shell', 'Web'],
    classifiers     = [
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],
)

setuptools_args = {}
setuptools_args['install_requires'] = [
    'facepy',
    'slackclient'
]

if 'setuptools' in sys.modules:
    setup_args.update(setuptools_args)


if __name__ == '__main__':
    setup(**setup_args)
