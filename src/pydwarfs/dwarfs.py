# -*- coding: utf-8 -*-
import errno
import os
import shutil
import subprocess as subproc
from typing import Any
from typing import Iterator
from typing import Mapping

import attrs

from pydwarfs.utils import get_mount_point

try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal

try:
    from typing import Self
except ImportError:
    from typing_extensions import Self

__all__ = ['DwarFS', 'DwarFSMountOptions', 'IsAMountPointError', 'NotAMountPointError', 'DwarfsUnmountError']


class IsAMountPointError(OSError):
    pass


class NotAMountPointError(OSError):
    pass


class DwarfsUnmountError(Exception):
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


def _validate_field_executable(__, ___, value: str) -> None:
    if not os.path.exists(value):
        raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), value)
    elif os.path.isdir(value):
        raise IsADirectoryError(errno.EISDIR, os.strerror(errno.EISDIR), value)
    elif not os.access(value, os.X_OK):
        raise PermissionError(errno.EPERM, os.strerror(errno.EPERM), value)
    elif not (basename := os.path.basename(value)) in ('dwarfs', 'dwarfs2'):
        raise ValueError(f'Invalid executable file name: {basename!r}')


@attrs.define(kw_only=True, slots=True)
class DwarFS:
    """
    The `DwarFS` class provides methods for mounting and unmounting DwarFS filesystems.

    Example Usage:
    ```python
    # Initialize DwarFS object
    dwarfs = DwarFS.init()

    # Mount a DwarFS filesystem
    dwarfs.mount('/path/to/image', '/path/to/mountpoint')

    # Unmount a DwarFS filesystem
    dwarfs.unmount('/path/to/mountpoint')
    ```

    Fields:
    - `executable: str`: The path to the DwarFS executable. It is required when initializing the `DwarFS` object.
    """

    executable: str = attrs.field(converter=os.fsdecode, validator=_validate_field_executable)

    @classmethod
    def init(cls, alter_executable: str | bytes | os.PathLike | None = None) -> Self:
        """
        Class method that initializes the `DwarFS` object.

        Args:
        - alter_executable: The path to the DwarFS executable. If not provided, it searches for the DwarFS executable in the system's $PATH.

        Returns:
        - The initialized `DwarFS` object.

        Raises:
        - FileNotFoundError: If the DwarFS executable is not found in the system $PATH.
        """
        if alter_executable is None:
            executable = shutil.which('dwarfs') or shutil.which('dwarfs2')
            if executable is None:
                raise FileNotFoundError('Could not find any dwarfs executable in the system $PATH')
        else:
            executable = alter_executable

        return cls(executable=executable)

    def mount(self,
              image: str | bytes | os.PathLike,
              mountpoint: str | bytes | os.PathLike,
              options: DwarFSMountOptions | Mapping[str, Any] | None = None,
              **kw_options
              ) -> subproc.CompletedProcess:
        """
        Mounts a DwarFS filesystem to the specified mountpoint.

        Args:
        - image: The path to the DwarFS image file.
        - mountpoint: The path to the mountpoint directory.
        - options: The options for mounting the DwarFS filesystem. It can be an instance of `DwarFSMountOptions` or a mapping of options.
        - **kw_options: Additional options passed as keyword arguments.

        Returns:
        - The `subproc.CompletedProcess` object representing the completed mount process.

        Raises:
        - FileNotFoundError: If the image file or mountpoint does not exist.
        - IsADirectoryError: If the image file is a directory.
        - PermissionError: If the image file or mountpoint is not accessible.
        """
        # Checking image accessibility
        image = os.fsdecode(image)
        if not os.path.exists(image):
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), image)
        elif os.path.isdir(image):
            raise IsADirectoryError(errno.EISDIR, os.strerror(errno.EISDIR), image)
        elif not os.access(image, os.R_OK):
            raise PermissionError(errno.EPERM, os.strerror(errno.EPERM), image)

        # Checking mountpoint accessibility
        mountpoint = os.fsdecode(mountpoint)
        if not os.path.exists(mountpoint):
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), mountpoint)
        elif os.path.ismount(mountpoint):
            raise IsAMountPointError(f'Already mounted as other filesystem: {mountpoint!r}')
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

        return subproc.run(cmdline, check=True)

    def unmount(self, mountpoint: str | bytes | os.PathLike,
                *, method: Literal['umount', 'fusermount'] = 'fusermount',
                lazy_unmount: bool = False
                ) -> subproc.CompletedProcess:
        """
        Unmounts a DwarFS filesystem from the specified mountpoint.

        Args:
        - mountpoint: The path to the mountpoint directory.
        - method: The unmount method. It can be either 'umount' or 'fusermount'. Default is 'fusermount'.
        - lazy_unmount: Whether to perform a lazy unmount. Default is False.

        Returns:
        - The `subproc.CompletedProcess` object representing the completed unmount process.

        Raises:
        - FileNotFoundError: If the mountpoint does not exist.
        - NotAMountPointError: If the mountpoint is not a valid DwarFS mountpoint.
        - DwarfsUnmountError: If the mountpoint is not a DwarFS filesystem mountpoint.
        - ValueError: If the unmount method is not 'umount' or 'fusermount'.
        - TypeError: If the unmount method is not a string.
        """
        if method == 'fusermount':
            if self.executable.endswith('2'):
                cmdline = ['fusermount', '-u']
            else:
                cmdline = ['fusermount3', '-u']
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

        mountpoint = os.fsdecode(mountpoint)
        if not os.path.exists(mountpoint):
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), mountpoint)
        if not os.path.ismount(mountpoint):
            raise NotAMountPointError(f'Not a mountpoint: {mountpoint!r}')
        else:
            mountpoint_info = get_mount_point(mountpoint)
            if not mountpoint_info:
                raise NotAMountPointError(f'Not a mountpoint: {mountpoint!r}')
            if mountpoint_info.fstype != 'fuse.dwarfs':
                raise DwarfsUnmountError(f'Not a DwarFS filesystem mountpoint: {mountpoint!r}')

        cmdline.append(mountpoint)

        return subproc.run(cmdline, check=True)
