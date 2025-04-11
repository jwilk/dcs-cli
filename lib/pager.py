# Copyright © 2015-2025 Jakub Wilk <jwilk@jwilk.net>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the “Software”), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

'''
automatic pager
'''

import contextlib
import io
import os
import subprocess as ipc
import sys

class Error(RuntimeError):
    pass

@contextlib.contextmanager
def autopager():
    if not sys.stdout.isatty():
        yield
        return
    cmdline = os.environ.get('PAGER', 'pager')
    if cmdline in {'', 'cat'}:
        yield
        return
    env = None
    if 'LESS' not in os.environ:
        env = dict(env or os.environ, LESS='-FXR')
    if 'LV' not in os.environ:
        env = dict(env or os.environ, LV='-c')
    orig_stdout = sys.stdout
    try:
        pager = ipc.Popen(cmdline, shell=True, stdin=ipc.PIPE, env=env)
        try:
            sys.stdout = io.TextIOWrapper(pager.stdin,
                encoding=orig_stdout.encoding,
                errors=orig_stdout.errors,
            )
            try:
                yield
            finally:
                sys.stdout.close()
        finally:
            pager.wait()
    finally:
        sys.stdout = orig_stdout
    if pager.returncode:
        raise Error

__all__ = [
    'Error',
    'autopager',
]

# vim:ts=4 sts=4 sw=4 et
