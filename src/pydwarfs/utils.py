# -*- coding: utf-8 -*-
import os
from pathlib import PosixPath as Path
from typing import Iterator

import attrs

try:
    from typing import Self
except ImportError:
    from typing_extensions import Self

__all__ = ['MountPoint', 'get_all_mount_points', 'get_mount_point']


@attrs.frozen(slots=True, kw_only=True)
class MountPoint:
    source: str
    target: Path
    fstype: str
    options: tuple[str, ...]
    freq: int
    passno: int

    def __fspath__(self) -> str:
        return os.fspath(self.target)

    @classmethod
    def parse(cls, line: str) -> Self:
        line_parts = line.rstrip().split()
        if len(line_parts) != 6:
            raise ValueError('')

        fs_spec = line_parts[0]
        fs_file = line_parts[1]
        fs_vfstype = line_parts[2]
        fs_mntops = tuple(line_parts[3].split(','))
        fs_freq = int(line_parts[4])
        fs_passno = int(line_parts[5])

        target = Path(str(bytes(fs_file, encoding='raw_unicode_escape'), encoding='unicode_escape'))

        return cls(source=fs_spec, target=target, fstype=fs_vfstype, options=fs_mntops, freq=fs_freq, passno=fs_passno)


def _iter_get_all_mounts_points() -> Iterator[MountPoint]:
    with open('/proc/mounts', mode='r') as f:
        for line in f:
            yield MountPoint.parse(line)


def get_all_mount_points() -> list[MountPoint]:
    return list(_iter_get_all_mounts_points())


def get_mount_point(fs_file: str | bytes | os.PathLike) -> MountPoint | None:
    fs_file_path = Path(os.fsdecode(fs_file))
    for mount_point in _iter_get_all_mounts_points():
        if mount_point.target.resolve() == fs_file_path.resolve():
            return mount_point
