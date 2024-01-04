# -*- coding: utf-8 -*-
import os

from packaging.version import Version

with open(os.path.join(os.path.dirname(__file__), 'VERSION')) as version_file:
    __version__ = version_file.readline().strip()
    __version_info__ = Version(__version__)


def version() -> str:
    return __version__


def version_info() -> Version:
    return __version_info__
