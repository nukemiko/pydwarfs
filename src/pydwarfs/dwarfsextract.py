# -*- encoding: utf-8 -*-
import errno
import io
import os
import shutil
import subprocess
from typing import Generator
from typing import Literal
from typing import overload

import attrs

from pydwarfs.exceptions import InvalidDwarFSImageFile
from pydwarfs.utils import AttrFieldValidatorFactory as AFVF

try:
    from typing import Self
except ImportError:
    from typing_extensions import Self

__all__ = ['DwarFSExtract', 'DwarFSExtractError']


class DwarFSExtractError(Exception):
    pass


@attrs.define(kw_only=True, slots=True)
class DwarFSExtract:
    """Class representing a DwarFS image extractor.

    Attributes:
        executable (str): The path to the 'dwarfsextract' executable.
    """
    executable: str = attrs.field(converter=os.fsdecode, validator=AFVF.executable_field('dwarfsextract'))

    @classmethod
    def init(cls, alter_executable: str | bytes | os.PathLike | None = None) -> Self:
        """Initializes a new instance of the DwarFSExtract class.

        Parameters:
            alter_executable (str | bytes | os.PathLike | None): The alternative path to the
                'dwarfsextract' executable. Default is None.

        Returns:
            A new instance of the DwarFSExtract class.
        """
        if alter_executable is None:
            executable = shutil.which('dwarfsextract')
            if executable is None:
                raise FileNotFoundError('Could not find any executable named {!s} in the system $PATH'.format('dwarfsextract'))
        else:
            executable = alter_executable

        return cls(executable=executable)

    @overload
    def extract(self,
                image: str | bytes | os.PathLike,
                output: str | bytes | os.PathLike,
                *, image_offset: int | Literal['auto'] | None = ...,
                continue_on_error: bool = ...,
                disable_integrity_check: bool = ...,
                yield_progress: Literal[False] = ...,
                workers: int | None = ...,
                cache_size: str | None = ...,
                log_level: Literal['error', 'warn', 'info', 'debug', 'trace'] | None = None
                ) -> None:
        pass

    @overload
    def extract(self,
                image: str | bytes | os.PathLike,
                output: str | bytes | os.PathLike,
                *, image_offset: int | Literal['auto'] | None = ...,
                continue_on_error: bool = ...,
                disable_integrity_check: bool = ...,
                yield_progress: Literal[True],
                workers: int | None = ...,
                cache_size: str | None = ...,
                log_level: Literal['error', 'warn', 'info', 'debug', 'trace'] | None = None
                ) -> Generator[int, None, None]:
        pass

    def extract(self, image, output,
                *, image_offset=None, continue_on_error=False, disable_integrity_check=False,
                yield_progress=False, workers=None, cache_size=None, log_level=None
                ):
        """
        Extracts a DwarFS image file.

        Parameters:
            image (str | bytes | os.PathLike): The path to the input DwarFS image file.
            output (str | bytes | os.PathLike): The path to the output directory where the extracted files will be saved.
            image_offset (int | Literal['auto'] | None): The offset of the image file, or 'auto'
                to automatically determine the offset. Default is None.
            continue_on_error (bool): Whether to continue extraction even if errors occur. Default is False.
            disable_integrity_check (bool): Whether to disable integrity checks during extraction. Default is False.
            yield_progress (bool): Whether to yield progress updates during extraction.
                Default is False.
            workers (int | None): The number of worker threads to use for extraction. Default is None.
            cache_size (str | None): Size of the block cache, in bytes.
                You can append suffixes (k, m, g) to specify the size in KiB, MiB and GiB, respectively.
                Default is None.
            log_level (Literal['error', 'warn', 'info', 'debug', 'trace'] | None):
                The log level for the extraction process. Default is None.

        Returns:
            If yield_progress is True, a generator that yields progress updates as integers.

            If yield_progress is False, None if the extraction process completes successfully.
            Otherwise, a DwarFSExtractError exception is raised.
        """
        image = os.path.abspath(os.fsdecode(image))
        with open(image, mode='rb') as f:
            if f.read(6) != b'DWARFS':
                raise InvalidDwarFSImageFile(f'Not a valid DwarFS image file: {image!r}')

        cmdline = [self.executable, '--input', image]

        output = os.path.abspath(os.fsdecode(output))
        if not os.path.exists(output):
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), output)
        elif not os.path.isdir(output):
            raise NotADirectoryError(errno.ENOTDIR, os.strerror(errno.ENOTDIR), output)
        elif not os.access(output, os.R_OK | os.W_OK | os.X_OK):
            raise PermissionError(errno.EPERM, os.strerror(errno.EPERM), output)
        cmdline.extend(['--output', output])

        if image_offset is not None:
            if isinstance(image_offset, int):
                image_offset_str = str(int(image_offset))
            elif str(image_offset) == 'auto':
                image_offset_str = 'auto'
            else:
                raise TypeError(
                    '{!r} must be an integer or a string {!r} (got {!r} that is {!r} object)'.format(
                        'image_offset', 'auto', image_offset, type(image_offset)
                    )
                )
            cmdline.extend(['--image-offset', image_offset_str])

        if continue_on_error:
            cmdline.append('--continue-on-error')

        if disable_integrity_check:
            cmdline.append('--disable-integrity-check')

        if yield_progress:
            cmdline.append('--stdout-progress')

        if workers is not None:
            if not isinstance(workers, int):
                raise TypeError
            cmdline.extend(['--workers', str(int(workers))])

        if cache_size is not None:
            if not isinstance(cache_size, str):
                raise TypeError
            cmdline.extend(['--cache-size', str(cache_size)])

        if log_level is not None:
            if not isinstance(log_level, str):
                raise TypeError
            elif str(log_level) not in ('error', 'warn', 'info', 'debug', 'trace'):
                raise ValueError
            cmdline.extend(['--log-level', str(log_level)])

        def progress_generator() -> Generator[int, None, None]:
            with subprocess.Popen(args=cmdline, stdout=subprocess.PIPE) as proc:
                stdout: io.BufferedReader = proc.stdout  # type: ignore
                while data := stdout.read1():
                    data = data.strip()
                    data_split = data.rsplit(b'\r', maxsplit=1)
                    if len(data_split) >= 1:
                        if len(data_split[-1]) > 1:
                            yield 100 - int(data_split[-1].removesuffix(b'%'))
            if proc.poll() != 0:
                raise DwarFSExtractError(f'Failed to extract DwarFS image file: {image!r}')

        if yield_progress:
            return progress_generator()

        try:
            subprocess.run(args=cmdline, check=True)
        except subprocess.CalledProcessError:
            raise DwarFSExtractError(f'Failed to extract DwarFS image file: {image!r}')
