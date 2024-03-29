# -*- encoding: utf-8 -*-
import errno
import os
import shutil
import subprocess as subproc
from typing import Any
from typing import Iterator
from typing import Literal
from typing import Mapping

import attrs
import mntfinder

from pydwarfs.exceptions import InvalidDwarFSImageFile
from pydwarfs.utils import AttrFieldValidatorFactory as AFVF

__all__ = ['DwarFS', 'DwarFSMountOptions', 'DwarFSError']


class DwarFSError(Exception):
    pass


@attrs.define(kw_only=True, slots=True)
class DwarFSMountOptions:
    cachesize: str | None = attrs.field(
        default=None,
        validator=attrs.validators.optional(attrs.validators.instance_of(str)),
        metadata={
            'cmdopt_tmpl': 'cachesize={!s}'
        }
    )
    workers: int | None = attrs.field(
        default=None,
        validator=attrs.validators.optional(attrs.validators.instance_of(int)),
        metadata={
            'cmdopt_tmpl': 'workers={!s}'
        }
    )
    mlock: Literal['try', 'must'] | None = attrs.field(  # type:ignore
        default=None,
        validator=attrs.validators.optional(
            attrs.validators.in_(('try', 'must'))
        ),
        metadata={
            'cmdopt_tmpl': 'mlock={!s}'
        }
    )
    decratio: int | float | None = attrs.field(
        default=None,
        validator=attrs.validators.optional(attrs.validators.instance_of((int, float))),
        metadata={
            'cmdopt_tmpl': 'decratio={!s}'
        }
    )
    offset: int | None = attrs.field(
        default=None,
        validator=attrs.validators.optional(attrs.validators.instance_of(int)),
        metadata={
            'cmdopt_tmpl': 'offset={!s}'
        }
    )
    enable_nlink: bool = attrs.field(
        default=False,
        validator=attrs.validators.optional(attrs.validators.instance_of(bool)),
        metadata={
            'cmdopt_tmpl': 'enable_nlink'
        }
    )
    readonly: bool = attrs.field(
        default=False,
        validator=attrs.validators.optional(attrs.validators.instance_of(bool)),
        metadata={
            'cmdopt_tmpl': 'readonly'
        }
    )
    cache_image: bool | None = attrs.field(
        default=None,
        validator=attrs.validators.optional(attrs.validators.instance_of(bool)),
        metadata={
            'cmdopt_tmpl'      : 'cache_image',
            'cmdopt_tmpl_false': 'no_cache_image'
        }
    )
    cache_files: bool | None = attrs.field(
        default=None,
        validator=attrs.validators.optional(attrs.validators.instance_of(bool)),
        metadata={
            'cmdopt_tmpl'      : 'cache_files',
            'cmdopt_tmpl_false': 'no_cache_files'
        }
    )
    debuglevel: Literal['error', 'warn', 'info', 'debug', 'trace'] | None = attrs.field(  # type:ignore
        default=None,
        validator=attrs.validators.optional(
            attrs.validators.in_(('error', 'warn', 'info', 'debug', 'trace'))
        ),
        metadata={
            'cmdopt_tmpl': 'debuglevel={!s}'
        }
    )
    tidy_strategy: Literal['time', 'swap'] | None = attrs.field(  # type:ignore
        default=None,
        validator=attrs.validators.optional(
            attrs.validators.in_(('time', 'swap'))
        ),
        metadata={
            'cmdopt_tmpl': 'tidy_strategy={!s}'
        }
    )
    tidy_interval: str | None = attrs.field(
        default=None,
        validator=attrs.validators.optional(attrs.validators.instance_of(str)),
        metadata={
            'cmdopt_tmpl': 'tidy_interval={!s}'
        }
    )
    tidy_max_age: str | None = attrs.field(
        default=None,
        validator=attrs.validators.optional(attrs.validators.instance_of(str)),
        metadata={
            'cmdopt_tmpl': 'tidy_max_age={!s}'
        }
    )

    def __iter__(self) -> Iterator[str]:
        def yield_options() -> Iterator[str]:
            attr: attrs.Attribute
            for attr in attrs.fields(type(self)):  # type:ignore
                attr_value = getattr(self, attr.name)
                if attr_value is not None:
                    if attr_value is False:
                        if attr.metadata.get('cmdopt_tmpl_false'):
                            yield '-o'
                            yield attr.metadata['cmdopt_tmpl_false']
                    elif attr_value is True:
                        yield '-o'
                        yield attr.metadata['cmdopt_tmpl']
                    else:
                        yield '-o'
                        yield attr.metadata['cmdopt_tmpl'].format(attr_value)

        return yield_options()


@attrs.define(kw_only=True, slots=True)
class DwarFS:
    """A class representing a DwarFS filesystem.

    Attributes:
        executable (str): The path to the ``dwarfs`` executable.
    """
    executable: str = attrs.field(converter=os.fsdecode, validator=AFVF.executableField(('dwarfs', 'dwarfs2')))

    @classmethod
    def init(cls, alter_executable: str | bytes | os.PathLike | None = None) -> 'DwarFS':
        """Initialize a DwarFS object.

        Parameters:
            alter_executable (str | bytes | os.PathLike | None, optional): Path to the `dwarfs` executable.
                If not provided, the executable will be searched for in the system $PATH. Defaults to `None`.

        Returns:
            DwarFS: A DwarFS object initialized with the specified executable.

        Raises:
            FileNotFoundError: If no `dwarfs` executable is found in the system $PATH.
        """
        if alter_executable is None:
            executable = shutil.which('dwarfs') or shutil.which('dwarfs2')
            if executable is None:
                raise FileNotFoundError('Could not find any executable named {!s} in the system $PATH'.format("'dwarfs' or 'dwarfs2'"))
        else:
            executable = alter_executable

        return cls(executable=executable)

    @staticmethod
    def isDwarFSMountPoint(target: str | bytes | os.PathLike) -> bool:
        return mntfinder.isMountPoint(target, fstype='fuse.dwarfs')

    @staticmethod
    def listAllDwarFSMountPoints() -> list[mntfinder.MountPoint]:
        return mntfinder.listAllMountPoints(fstype='fuse.dwarfs')

    def mount(self,
              image: str | bytes | os.PathLike,
              mountpoint: str | bytes | os.PathLike,
              options: DwarFSMountOptions | Mapping[str, Any] | None = None,
              **kw_options
              ) -> None:
        image = os.fsdecode(os.path.realpath(image))
        with open(image, mode='rb') as f:
            if f.read(6) != b'DWARFS':
                raise InvalidDwarFSImageFile(f'Not a valid DwarFS image file: {image!r}')

        mountpoint = os.fsdecode(os.path.realpath(mountpoint))
        if mntfinder.isMountPoint(mountpoint):
            raise DwarFSError(f'Already mounted as other filesystem: {mountpoint!r}')
        elif not os.path.exists(mountpoint):
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), mountpoint)
        elif not os.path.isdir(mountpoint):
            raise NotADirectoryError(errno.ENOTDIR, os.strerror(errno.ENOTDIR), mountpoint)
        elif not os.access(mountpoint, os.R_OK | os.W_OK | os.X_OK):
            raise PermissionError(errno.EPERM, os.strerror(errno.EPERM), mountpoint)

        cmdline = [self.executable, image, mountpoint]
        if isinstance(options, DwarFSMountOptions):
            options_instance = options
        elif options is not None:
            options_instance = DwarFSMountOptions(**options)
        else:
            options_instance = DwarFSMountOptions()
        options_instance = attrs.evolve(options_instance, **kw_options)

        cmdline.extend(options_instance)

        try:
            subproc.run(cmdline, check=True)
        except subproc.CalledProcessError:
            raise DwarFSError(f'Failed to mount the image file {image!r} to {mountpoint!r}')

    @classmethod
    def unmount(cls, mountpoint: str | bytes | os.PathLike,
                *, method: Literal['umount', 'fusermount'] = 'fusermount',
                lazy_unmount: bool = False
                ) -> None:
        if method == 'fusermount':
            fusermount_path = shutil.which('fusermount') or shutil.which('fusermount3')
            if not fusermount_path:
                raise DwarFSError(f'Cannot find fusermount or fusermount3 to unmount {mountpoint!r}')
            cmdline = [fusermount_path, '-u']
            if lazy_unmount:
                cmdline.append('-z')
        elif method == 'umount':
            cmdline = ['umount']
            if lazy_unmount:
                cmdline.append('--lazy')
        elif isinstance(method, str):
            raise ValueError(f"unmoount method must be 'umount' or 'fusermount' (got {method!r})")
        else:
            raise TypeError(f"'method' must be either 'umount' or 'fusermount' (got {type(method)!r})")

        mountpoint = os.path.abspath(os.fsdecode(mountpoint))
        if not cls.isDwarFSMountPoint(mountpoint):
            raise DwarFSError(f'Not a DwarFS filesystem mountpoint: {mountpoint!r}')
        if not os.path.exists(mountpoint):
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), mountpoint)

        cmdline.append(mountpoint)

        try:
            subproc.run(cmdline, check=True)
        except subproc.CalledProcessError:
            raise DwarFSError(f'Failed to unmount: {mountpoint!r}')
