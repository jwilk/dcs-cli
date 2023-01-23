# Copyright © 2015-2023 Jakub Wilk <jwilk@jwilk.net>
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
command-line interface
'''

import argparse
import html
import json
import os
import re
import signal
import sys
import time
import urllib.parse
import urllib.request

import websocket

from lib import colors
from lib import pager
from lib import somber

host = 'codesearch.debian.net'
user_agent = 'dcs-cli (https://github.com/jwilk/dcs-cli)'

keyword_types = {
    'filetype',
    'package',
    'pkg',
    'path',
}

is_keyword = re.compile(
    '^-?(?:{0}):'.format('|'.join(keyword_types))
).match

def lsplit(pred, lst):
    lyes = []
    lno = []
    for item in lst:
        if pred(item):
            lyes += [item]
        else:
            lno += [item]
    return (lyes, lno)

def xmain():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ignore-case', '-i', action='store_true', help='ignore case distinctions')
    ap.add_argument('--word-regexp', '-w', action='store_true', help='match only whole words')
    ap.add_argument('--fixed-string', '-F', '-Q', action='store_true', help='interpret pattern as fixed string')
    ap.add_argument('--context', '-C', metavar='N', default=2, type=int, help='print N lines of output context (default: 2)')
    ap.add_argument('--color', choices=('never', 'always', 'auto'), default='auto', help='when to use colors (default: auto)')
    ap.add_argument('--web-browser', '-W', action='store_true', help='spawn a web browser')
    ap.add_argument('--delay', default=200, type=int, help='minimum time between requests, in ms (default: 200)')
    ap.add_argument('query', metavar='QUERY')
    ap.add_argument('query_tail', nargs='*', help=argparse.SUPPRESS)
    options = ap.parse_args()
    if options.context < 0:
        options.context = 0
    elif options.context > 2:
        options.context = 2
    if (options.color == 'always') or (options.color == 'auto' and sys.stdout.isatty()):
        options.output = colors
    else:
        options.output = somber
    options.delay /= 1000
    query = [options.query] + options.query_tail
    [keywords, query] = lsplit(is_keyword, query)
    query = ' '.join(query)
    if options.fixed_string:
        query = re.escape(query)
    if options.word_regexp:
        if '|' in query:
            query = f'(?:{query})'
        query = fr'\b{query}\b'
    if options.ignore_case:
        query = '(?i)' + query
    options.query_regexp = query
    query = ' '.join([query] + keywords)
    options.query = query
    if options.web_browser:
        send_web_query(options)
        return
    with pager.autopager():
        send_query(options)

def main():
    try:
        xmain()
    except BrokenPipeError:
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)
        os.kill(os.getpid(), signal.SIGPIPE)
        raise

def send_web_query(options):
    url = (
        'https://codesearch.debian.net/search?q=' +
        urllib.parse.quote_plus(options.query)
    )
    browser = 'sensible-browser'
    os.execvp(browser, [browser, url])

def wget_json(query_id, s):
    url = 'https://{host}/results/{qid}/{s}.json'.format(
        host=host,
        qid=query_id,
        s=s,
    )
    request = urllib.request.Request(url, headers={'User-Agent': user_agent})
    try:
        with urllib.request.urlopen(request) as fp:
            data = fp.read()
    except urllib.error.HTTPError as exc:
        exc.msg += ' <' + exc.url + '>'
        raise
    data = data.decode('UTF-8')
    data = json.loads(data)
    return data

def send_query(options):
    query = options.query
    output = options.output
    output.print('Query: {t.bold}{q}{t.off}', q=query)
    sys.stdout.flush()
    query = dict(Query=('q=' + urllib.parse.quote(query)))
    query = json.dumps(query)
    socket = websocket.WebSocket()
    socket.connect(
        f'wss://{host}/instantws',
        header=['User-Agent: ' + user_agent]
    )
    socket.send(query)
    n_pages = None
    while True:
        msg = socket.recv()
        msg = json.loads(msg)
        tp = msg.get('Type', 'default')
        if tp == 'progress':
            if msg['FilesProcessed'] != msg['FilesTotal']:
                continue
            query_id = msg['QueryId']
            n_results = msg['Results']
            output.print('Results: {n}', n=n_results)
            sys.stdout.flush()
            if n_results == 0:
                break
            packages = wget_json(query_id, 'packages')['Packages']
            ts = time.time()
            output.print('Packages: {n} ({pkgs})',
                n=len(packages),
                pkgs=' '.join(packages),
            )
            print()
            sys.stdout.flush()
            for n in range(n_pages):
                new_ts = time.time()
                td = new_ts - ts
                if td < options.delay:
                    time.sleep(options.delay - td)
                ts = new_ts
                data = wget_json(query_id, f'page_{n}')
                print_results(options, data)
            break
        elif tp == 'pagination':
            n_pages = msg['ResultPages']
        elif tp == 'error':
            if msg['ErrorType'] == 'invalidquery':
                print('DCS error: invalid query', file=sys.stderr)
                sys.exit(1)
            elif msg['ErrorType'] == 'backendunavailable':
                print('DCS error: backend server is not available', file=sys.stderr)
                sys.exit(1)
            raise NotImplementedError(msg)
        elif tp == 'default':
            continue
        else:
            raise NotImplementedError(msg)
    socket.close()

def xsplit(regexp, string):
    prev_end = 0
    if isinstance(regexp, str):
        regexp = re.compile(regexp)
    for match in regexp.finditer(string):
        start, end = match.span()
        if start > prev_end:
            yield string[prev_end:start], False
        yield string[start:end], True
        prev_end = end
    if prev_end < len(string):
        yield string[prev_end:], False

def compile_query_regexp(query_regexp):
    def repl(match):
        (flags, main) = match.groups()
        return f'{flags or ""}({main})'
    regexp = re.sub(r'\A([(][?][^)]+[)])?(.*)\Z', repl, query_regexp, flags=re.DOTALL)
    try:
        return re.compile(regexp)
    except re.error:
        return re.compile(r'\Zx')  # never match anything

def print_results(options, items):
    output = options.output
    query_regexp = compile_query_regexp(options.query_regexp)
    for item in items:
        output.print('{path}:{line}:', pkg=item['package'], path=item['path'], line=item['line'])
        context = [item['ctxp2'], item['ctxp1']]
        context = context[(2 - options.context):]
        for line in context:
            line = html.unescape(line)
            output.print('{t.dim}|{t.off} {line}', line=line)
        line = html.unescape(item['context'])
        template = '{t.dim}>{t.off} '
        chunkdict = {}
        for i, (chunk, matched) in enumerate(xsplit(query_regexp, line)):
            chunkdict[f'l{i}'] = chunk
            template += '{t.bold}'
            if matched:
                template += '{t.yellow}'
            template += '{l' + str(i) + '}{t.off}'
        output.print(template, **chunkdict)
        context = item['ctxn1'], item['ctxn2']
        context = context[:options.context]
        for line in context:
            line = html.unescape(line)
            output.print('{t.dim}|{t.off} {line}', line=line)
        output.print('{t.dim}(pathrank {pathrank:.4f}, rank {rank:.4f}){t.off}',
            pathrank=item['pathrank'],
            rank=item['ranking'],
        )
        print()
        sys.stdout.flush()

__all__ = ['main']

# vim:ts=4 sts=4 sw=4 et
