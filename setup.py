import os
import sys

import setuptools


# Avoid polluting the .tar.gz with ._* files under Mac OS X
os.putenv('COPYFILE_DISABLE', 'true')

root = os.path.dirname(__file__)

# Prevent distutils from complaining that a standard file wasn't found
README = os.path.join(root, 'README')
if not os.path.exists(README):
    os.symlink(README + '.rst', README)

description = "A bridge between mesh and LAN networks via serial"

with open(os.path.join(root, 'README'), encoding='utf-8') as f:
    long_description = '\n\n'.join(f.read().split('\n\n')[1:])

version = None
with open(os.path.join(root, 'hemma-bridge', 'version.py'), encoding='utf-8') as f:
    exec(f.read())

py_version = sys.version_info[:2]

if py_version < (3, 3):
    raise Exception("hemma-bridge requires Python >= 3.3.")

setuptools.setup(
    name='hemma-bridge',
    version=version,
    author='Bas Peschier',
    author_email='bpeschier@fizzgig.nl',
    url='https://github.com/bpeschier/hemma-bridge',
    description=description,
    long_description=long_description,
    packages=[
        'bridge',
    ],
    install_requires=[
        'flynn>=1,<2',
        'pyserial>=3,<4',
        'websockets>=3,<4',
        'zeroconf>=0.17,<0.18',
    ],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
    ],
    platforms='all',
    license='MIT'
)
