# PyDwarfs

A wrapper of DwarFS command line utilities.

DwarFS is stands for **Deduplicating Warp-speed Advanced Read-only File System**, it is a fast high compression read-only file system for Linux and Windows. [See this project's homepage.](https://github.com/mhx/dwarfs)

**Note: This project currently does not provide support for Windows version of DwarFS command line utility.**

## Features / TODO

- [x] Mount/unmount a DwarFS image file to specified mountpoint (`dwarfs`/`mount.dwarfs`)
- [x] Extract a DwarFS image file (`dwarfsextract`, initially implemented)
- [ ] Create a DwarFS image file (`mkdwarfs`)
- [ ] Check a DwarFS image file (`dwarfsck`)
- [ ] Performance test (`dwarfsbench`)

## Install

Just run the command: `pip install pydwarfs`.

Or you can download and install the wheel file from release page manually.

## Examples

The following examples are for the more common uses of command line utilities.

### Mount/unmount a DwarFS image file to specified mountpoint

#### Create a `DwarFS` instance

In the default case, `Dwarfs.init()` will find the location of `dwarfs` command via `shutil.which()`.

```pycon
>>> from pydwarfs.dwarfs import DwarFS
>>> dwarfs = Dwarfs.init()
>>> dwarfs.executable
'/usr/bin/dwarfs'
>>>
```

If the DwarFS command line utilities are not installed, you can specify a location of `dwarfs` command instead.

```
>>> from pydwarfs.dwarfs import DwarFS
>>> dwarfs = Dwarfs.init('/path/to/valid/dwarfs')
>>> dwarfs.executable
'/path/to/valid/dwarfs'
>>>
```

#### A simple mount

```pycon
>>> dwarfs.mount('/path/to/source.dwarfs', '/path/to/destination/directory')
>>>
```

To check if the mount was actually successful, exit the Python REPL and run the following command:

```sh-session
$ > findmnt /path/to/destination/directory
TARGET                         SOURCE FSTYPE      OPTIONS
/path/to/destination/directory dwarfs fuse.dwarfs rw,nosuid,nodev,relatime,user_id=1000,group_id=1000
$ >
```

#### Mount with some specified options

Use the dedicated attribute class `DwarFSMountOptions`:

```pycon
>>> from pydwarfs.dwarfs import DwarFS, DwarFSMountOptions
>>> dwarfs = Dwarfs.init()
>>> options1 = DwarFSMountOptions(cachefile='32M', readonly=True, debuglevel='debug')
>>> dwarfs.mount('/path/to/source.1.dwarfs', '/path/to/destination/directory.1', options)
I 04:06:32.182380 [dwarfs_main.cpp:1328] dwarfs (v0.7.4, fuse version 35)
D 04:06:32.182909 [filesystem_v2.cpp:482] found valid section index
D 04:06:32.182927 [filesystem_v2.cpp:493] section BLOCK @ 64 [16,669,939 bytes]
...
D 04:06:32.191025 [filesystem_v2.cpp:515] read 734 blocks and 175,158 bytes of metadata
I 04:06:32.191041 [dwarfs_main.cpp:1144] file system initialized [8.624ms]
>>>
```

Or simply specify options by dict and **kwargs:

```pycon
>>> from pydwarfs.dwarfs import DwarFS, DwarFSMountOptions
>>> dwarfs = Dwarfs.init()
>>> options2 = {'cachefile': '16M', 'readonly': True}
>>> dwarfs.mount('/path/to/source.2.dwarfs', '/path/to/destination/directory.2', options, debuglevel='debug')
I 04:14:01.981335 [dwarfs_main.cpp:1328] dwarfs (v0.7.4, fuse version 35)
D 04:14:01.983736 [filesystem_v2.cpp:482] found valid section index
D 04:14:01.983753 [filesystem_v2.cpp:493] section BLOCK @ 64 [67,097,028 bytes]
...
D 04:14:01.984644 [filesystem_v2.cpp:515] read 7 blocks and 2,755 bytes of metadata
I 04:14:01.984656 [dwarfs_main.cpp:1144] file system initialized [3.27ms]
>>>
```

#### Unmount

```pycon
>>> dwarfs.unmount('/path/to/destination/directory')
>>>
```

Unmount by the method `umount` instead of the default `fusermount`:

```pycon
>>> dwarfs.unmount('/path/to/destination/directory.1', method='umount')
>>>
```

You can forcely unmount by add the argument `lazy_unmount=True`:

```pycon
>>> dwarfs.unmount('/path/to/destination/directory.2', lazy_unmount=True)
>>>
```

### Extract a DwarFS image file

#### A simple extraction

```pycon
>>> import os
>>> from pydwarfs.dwarfsextract import DwarFSExtract
>>> dwarfsextract = DwarFSExtract.init()
>>> output_dir = '/path/to/dest/directory'
>>> dwarfsextract.extract('/path/to/image.dwarfs', output_dir)
>>>
>>> os.listdir(output_dir)
['dataWin', 'Sakuna.exe', 'steam_appid.txt', 'xaudio2_9redist.dll', ...]
>>>
```

**Note:** The path pointed to by `output_dir` must be an existing directory.

#### Extract image file with progress

```pycon
>>> another_output_dir = '/path/to/another/output/directory'
>>> for progress in dwarfsextract.extract('/path/to/image.dwarfs', another_output_dir, yield_progress=True):
...     print(progress)
...
100
99
98
...
2
1
0
>>> os.listdir(another_output_dir)
['dataWin', 'Sakuna.exe', 'steam_appid.txt', 'xaudio2_9redist.dll', ...]
>>>
```
