# Copyright © 2015 Jakub Wilk <jwilk@jwilk.net>
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
color terminal support
'''

import builtins
import re

class _seq:
    dim = '\x1b[1;30m'
    off = '\x1b[0m'
    bold = '\x1b[1m'
    yellow = '\x1b[33m'
    reverse = '\x1b[7m'
    unreverse = '\x1b[27m'

def _quote_unsafe_char(ch):
    if ch == '\t':
        return '{t.reverse}\t{t.unreverse}'.format(t=_seq)
    elif ch < ' ' or ch == '\x7F':
        return '{t.reverse}^{c}{t.unreverse}'.format(t=_seq, c=chr(ord('@') ^ ord(ch)))
    else:
        return '{t.reverse}<U+{u:04X}>{t.unreverse}'.format(t=_seq, u=ord(ch))

def _quote_unsafe(s):
    return ''.join(map(_quote_unsafe_char, s))

def _quote(s):
    if not isinstance(s, str):
        return s
    chunks = re.split(r'([\x00-\x1F\x7F-\x9F]+)', s)
    def esc():
        for i, s in enumerate(chunks):
            if i & 1:
                yield _quote_unsafe(s)
            else:
                yield s
    return ''.join(esc())

def format(_s, **kwargs):
    kwargs.update(t=_seq)
    return _s.format(**{
        key: _quote(value)
        for key, value in kwargs.items()
    })

def print(_s='', **kwargs):
    builtins.print(format(_s, **kwargs))

__all__ = [
    'format',
    'print',
]

# vim:ts=4 sts=4 sw=4 et
