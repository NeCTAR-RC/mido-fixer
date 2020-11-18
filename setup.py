#!/usr/bin/env python

import setuptools

from pbr.packaging import parse_requirements


setuptools.setup(
    name='mido-fixer',
    version='0.1.0',
    description='Fix the Mido!',
    long_description='Fix the Mido!',
    author='Sam Morrison',
    author_email='sorrison@gmail.com',
    url='https://github.com/NeCTAR-RC/mido-fixer',
    packages=[
        'mido_fixer',
    ],
    entry_points={
        'console_scripts': [
            'mido-fixer = mido_fixer.cmd:main',
        ],
    },
    install_requires=parse_requirements(),
    license="GPLv3+",
    zip_safe=False,
    keywords='mido',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        ('License :: OSI Approved :: '
         'GNU General Public License v3 or later (GPLv3+)'),
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
    ],
)
