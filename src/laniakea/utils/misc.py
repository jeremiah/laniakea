# -*- coding: utf-8 -*-
#
# Copyright (C) 2016-2022 Matthias Klumpp <matthias@tenstral.net>
#
# SPDX-License-Identifier: LGPL-3.0+

import os
import re
import fcntl
from typing import Union
from datetime import datetime
from contextlib import contextmanager

import requests

import laniakea.typing as T


def get_dir_shorthand_for_uuid(uuid):
    '''
    Get short prefix for UUIDs for use in directory names.
    '''
    s = str(uuid)

    if len(s) > 2:
        return s[0:2]
    return None


def random_string(length=8):
    '''
    Generate a random alphanumerical string with length :length.
    '''
    import random
    import string

    return ''.join([random.choice(string.ascii_letters + string.digits) for n in range(length)])


@contextmanager
def cd(where):
    ncwd = os.getcwd()
    try:
        yield os.chdir(where)
    finally:
        os.chdir(ncwd)


def listify(item):
    '''
    Return a list of :item, unless :item already is a lit.
    '''
    if not item:
        return []
    return item if type(item) == list else [item]


def stringify(item):
    '''
    Convert anything into a string, if it isn't one already.
    Assume UTF-8 encoding if we have bytes.
    '''
    if type(item) is str:
        return item
    if type(item) is bytes:
        return str(item, 'utf-8')

    return str(item)


def is_remote_url(uri):
    '''Check if string contains a remote URI.'''

    uriregex = re.compile('^(https?|ftps?)://')
    return uriregex.match(uri) is not None


def download_file(url, fname, check=False, headers: dict = None, **kwargs):

    if not headers:
        headers = {}

    hdr = {'user-agent': 'laniakea/0.0.1'}
    hdr.update(headers)

    r = requests.get(url, stream=True, headers=hdr, **kwargs)
    if r.status_code == 200:
        with open(fname, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024):
                f.write(chunk)
        return r.status_code

    if check:
        raise Exception('Unable to download file "{}". Status: {}'.format(url, r.status_code))
    return r.status_code


@contextmanager
def open_compressed(fname, mode='rb'):
    '''
    Open a few compressed filetypes easily.
    '''

    lower_fname = fname.lower()
    f = None
    if lower_fname.endswith('.xz'):
        import lzma

        f = lzma.open(fname, mode=mode)
    elif lower_fname.endswith('.gz'):
        import gzip

        f = gzip.open(fname, mode=mode)
    else:
        raise Exception('Can not decompress file (compression type not recognized): {}'.format(fname))

    try:
        yield f
    finally:
        f.close()


def split_strip(s, sep):
    '''Split a string, removing empty segments from the result and stripping the individual parts'''
    res = []
    for part in s.split(sep):
        if part:
            res.append(part.strip())
    return res


# Match safe filenames
re_file_safe = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9_.~+-]*$')

# Match safe filenames, including slashes
re_file_safe_slash = re.compile(r'^[a-zA-Z0-9][/a-zA-Z0-9_.~+-]*$')


def check_filename_safe(fname: Union[os.PathLike, str]) -> bool:
    """Check if a filename contains only safe characters"""
    if not re_file_safe.match(str(fname)):
        return False
    return True


def check_filepath_safe(path: Union[os.PathLike, str]) -> bool:
    """Check if a filename contains only safe characters"""
    if not re_file_safe_slash.match(str(path)):
        return False
    return True


def datetime_to_rfc2822_string(dt: datetime):
    """Convert a datetime object into an RFC2822 date string."""
    from email import utils

    return utils.format_datetime(dt)


def safe_rename(src: T.PathUnion, dst: T.PathUnion, *, override: bool = False):
    '''
    Instead of directly moving a file with rename(), copy the file
    and then delete the original.
    Also reset the permissions on the resulting copy.
    '''

    from shutil import copy2

    if override and os.path.isfile(dst):
        os.unlink(dst)
    new_fname = copy2(src, dst)
    os.chmod(new_fname, 0o755)
    os.unlink(src)


class ProcessFileLock:
    """
    Simple wy to prevent multiple processes from executing the same code via a file lock.
    """

    def __init__(self, name: str):
        """
        :param name: Unique name of the lock.
        """
        self._name = name
        self._lock_file_fd = -1
        self._lock_dir = os.path.join('/usr/user', str(os.geteuid()))
        if not os.path.isdir(self._lock_dir):
            self._lock_dir = '/tmp'  # may also be /var/lock

    @property
    def lock_filename(self) -> str:
        return os.path.join(self._lock_dir, 'laniakea_' + self._name + '.lock')

    def acquire(self, raise_error=True) -> bool:
        """
        Try to acquire a lockfile with the given name, useful to ensure only one process is executing a critical
        section at a time.
        :param raise_error: True if we should raise an error, instead of just returning False if lock can't be acquired.
        :return: True if lock was acquired.
        """
        fd = os.open(self.lock_filename, os.O_RDWR | os.O_CREAT)
        try:
            fcntl.lockf(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except IOError:
            # another instance is running
            self._lock_file_fd = -1
            os.close(fd)
            if raise_error:
                raise Exception('Unable to acquire lock "{}": Another instance is running!'.format(lock_fname))
            return False
        self._lock_file_fd = fd
        return True

    def release(self):
        """Release an acquired lock. Does nothing if no lock was taken."""
        if self._lock_file_fd <= 0:
            return
        fcntl.lockf(self._lock_file_fd, fcntl.LOCK_UN)
        os.close(self._lock_file_fd)
        self._lock_file_fd = -1


@contextmanager
def process_file_lock(name: str, *, raise_error=True):
    flock = ProcessFileLock(name)
    flock.acquire(raise_error)
    try:
        yield flock
    finally:
        flock.release()
