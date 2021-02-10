#!/usr/bin/env python3
# The MIT License
# 
# Copyright (c) 2021 Christian C. Sachs
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


# Simple and fast read-only ZIP file mount using Python and FUSE
# see https://github.com/csachs/pyfusezip

# Requires the Python FUSE library, e.g. `apt install python3-fuse` for Ubuntu

__version__ = '0.0.1'

import errno
import stat

import datetime
import os

import zipfile

import fuse

fuse.fuse_python_api = (0, 2)


def path_split(what):
    return what.split('/')


def path_join(*args):
    return '/'.join(args)


CACHING_CACHE_NONE, CACHING_CACHE_CONTENTS, CACHING_CACHE_FP = 0, 1, 2
USE_CACHING = CACHING_CACHE_FP


class PyFuseZip(fuse.Fuse):

    def __init__(self, *args, **kwargs):
        self.zipfile = None
        self.zip_dirs = {}
        self.zip_dir_shortcuts = {}

        self.cache = {}

        self.uid = 0
        self.gid = 0

        super().__init__(*args, dash_s_do='setsingle', **kwargs)

        self.fuse_args.optlist.add('ro')  # only ro support
        self.multithreaded = False  # currently no support for MT. parallel access to zipfiles reading will lead to segv

    def main(self, args=None):
        _, real_args = self.cmdline

        if len(real_args) != 1:
            raise RuntimeError("Pass exactly one additional argument, the desired archive to mount.")

        input_file = real_args[0]

        self.uid = os.getuid()
        self.gid = os.getgid()

        self.zipfile = zipfile.ZipFile(input_file)

        for item in self.zipfile.infolist():
            self.zip_dir_shortcuts[item.filename] = item
            all_path_fragments = path_split(item.filename)
            dir_fragments, file_name = all_path_fragments[:-1], all_path_fragments[-1]

            path_so_far = []

            current_position = self.zip_dirs

            for fragment in dir_fragments:
                if fragment not in current_position:
                    current_position[fragment] = {}

                current_position = current_position[fragment]
                path_so_far.append(fragment)
                self.zip_dir_shortcuts[path_join(*path_so_far)] = current_position

            current_position[file_name] = item

        self.zip_dir_shortcuts[''] = self.zip_dirs

        super().main(args)

    def getattr(self, path):
        def find_first_file(d):
            for item_or_dict in d.values():
                if isinstance(item_or_dict, zipfile.ZipInfo):
                    return item_or_dict
                else:
                    return find_first_file(item_or_dict)

        if path.startswith('/'):
            path = path[1:]

        st = fuse.Stat()
        if path == '':
            st.st_mode = stat.S_IFDIR | 0o755
            st.st_nlink = 2
        elif path in self.zip_dir_shortcuts:
            item = self.zip_dir_shortcuts[path]
            if isinstance(item, dict):
                st.st_mode = stat.S_IFDIR | 0o755
                st.st_nlink = 2
                ts = datetime.datetime(*find_first_file(item).date_time).timestamp()

            elif isinstance(item, zipfile.ZipInfo):
                st.st_mode = stat.S_IFREG | 0o444
                st.st_nlink = 1
                st.st_size = item.file_size

                ts = datetime.datetime(*item.date_time).timestamp()
            else:
                raise RuntimeError('This should  never happen.')

            st.st_atime = ts
            st.st_mtime = ts
            st.st_ctime = ts

            st.st_uid = self.uid
            st.st_gid = self.gid
        else:
            return -errno.ENOENT

        return st

    def readdir(self, path, offset):
        if path.startswith('/'):
            path = path[1:]

        assert offset == 0  # we don't handle offset-ed readddir

        if path in self.zip_dir_shortcuts:
            yield fuse.Direntry('.')
            yield fuse.Direntry('..')

            for item in self.zip_dir_shortcuts[path].keys():
                yield fuse.Direntry(item)
        else:
            return -errno.ENOENT

    def open(self, path, flags):
        if path.startswith('/'):
            path = path[1:]
        if path in self.zip_dir_shortcuts:
            accmode = os.O_RDONLY | os.O_WRONLY | os.O_RDWR

            if (flags & accmode) != os.O_RDONLY:
                return -errno.EACCESS
        else:
            return -errno.ENOENT

    def read(self, path, size, offset):
        if path.startswith('/'):
            path = path[1:]

        if path in self.zip_dir_shortcuts:
            item = self.zip_dir_shortcuts[path]

            if USE_CACHING == 1:
                if path not in self.cache:
                    self.cache.clear()
                    self.cache[path] = self.zipfile.read(item)
                return self.cache[path][offset:offset+size]
            elif USE_CACHING == 2:
                if path not in self.cache:
                    self.cache.clear()
                    self.cache[path] = self.zipfile.open(item)
                self.cache[path].seek(offset)
                return self.cache[path].read(size)
            else:
                with self.zipfile.open(item) as fp:
                    fp.seek(offset)
                    return fp.read(size)

        else:
            return -errno.ENOENT


def main():
    server = PyFuseZip(version='PyFuseZip', usage=PyFuseZip.fusage)
    server.parse(errex=1)
    server.main()


if __name__ == '__main__':
    main()
