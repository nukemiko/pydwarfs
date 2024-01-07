# -*- encoding: utf-8 -*-
import errno
import os
from typing import Any
from typing import Callable

import attrs

__all__ = ['AttrFieldValidatorFactory']


class AttrFieldValidatorFactory:
    @staticmethod
    def executableField(basename: str | tuple[str, ...]) -> Callable[[Any, attrs.Attribute, Any], None]:
        def validator(__: Any, ___: attrs.Attribute, value: Any) -> None:
            if not os.path.exists(value):
                raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), value)
            elif os.path.isdir(value):
                raise IsADirectoryError(errno.EISDIR, os.strerror(errno.EISDIR), value)
            elif not os.access(value, os.X_OK):
                raise PermissionError(errno.EPERM, os.strerror(errno.EPERM), value)

            actual_basename = os.path.basename(value).lower()
            if isinstance(basename, tuple):
                basenames: list[str] = [s.lower() for s in basename]
                if actual_basename not in basenames:
                    raise ValueError(f'Executable name must be one of the following: {basenames!r} (got {actual_basename!r})')
            elif actual_basename != basename.lower():
                raise ValueError(f'Executable name must be {basename!r} (got {actual_basename!r}')

        return validator
