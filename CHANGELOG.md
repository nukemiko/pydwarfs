# Changelog

All notable changes to this project will be documented in this file.

This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html). Simplified Chinese version at [here](https://semver.org/lang/zh-CN/spec/v2.0.0.html).

## <span id="changelog-20240107-0-3-0">0.3.0 - 2024-01-07</span>

This version contains some **BREAKING changes**:

### Dependency

- Removed dependency `packaging`.
    - Now the version number can only be queried through `pydwarfs.__version__`.
- Added dependency `mntfinder` to better find/check/list mountpoints.

### Project

- Changes of classes/methods/functions:
    - `pydwarfs.dwarfs`
        - Added
            - Static method `DwarFS.isDwarFSMountPoint()`: to check if a path is DwarFS mountpoint
            - Static method `DwarFS.listAllDwarFSMountPoints()`: to list all of DwarFS mountpoints.
        - Removed
            - All can be instead by `DwarFSError`:
                - Class `IsAMountPointError`
                - Class `NotAMountPointError`
                - Class `DwarFSMountError`
                - Class `DwarFSUnmountError`
    - `pydwarfs.utils`
        - Changed
            - `AttrFieldValidatorFactory.executable_field` -> `AttrFieldValidatorFactory.executableField`
        - Removed
            - They are became redundant due to the introduction of new dependency `mntfinder`:
                - Class `MountPoint`
                - Function `get_all_mount_points`
                - Function `get_mount_point`

## 0.2.1 - 2024-01-06

- Added docstrings for `DwarFSExtract` and it's methods.

## 0.2.0 - 2024-01-06

- Initially implemented the DwarFS image file extraction.

## 0.1.1 - 2024-01-06

- Improved parsing of /proc/mounts
- Improved the process before mounting and unmounting
- Changed the return value of `DwarFS.mount() `and `DwarFS.unmount()` (now they both return `None`)

## 0.1.0 - 2024-01-05

Initial release.
