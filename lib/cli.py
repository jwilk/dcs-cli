#!/usr/bin/python3

# Copyright © 2015-2016 Jakub Wilk <jwilk@jwilk.net>
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
import sys
import urllib.parse
import urllib.request
import websocket

from lib import colors
from lib import pager

host = 'codesearch.debian.net'
user_agent = 'dcs-cli (https://github.com/jwilk/dcs-cli)'

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ignore-case', '-i', action='store_true')
    ap.add_argument('--word-regexp', '-w', action='store_true')
    ap.add_argument('query', metavar='QUERY')
    options = ap.parse_args()
    query = options.query
    if options.word_regexp:
        query = r'\b{query}\b'.format(query=query)
    if options.ignore_case:
        query = '(?i)' + query
    with pager.autopager():
        send_query(options, query)

def wget_json(query_id, s):
    url = 'https://{host}/results/{qid}/{s}.json'.format(
        host=host,
        qid=query_id,
        s=s,
    )
    request = urllib.request.Request(url, headers={'User-Agent': user_agent})
    with urllib.request.urlopen(request) as fp:
        data = fp.read()
    data = data.decode('UTF-8')
    data = json.loads(data)
    return data

def send_query(options, query):
    colors.print('Query: {t.bold}{q}{t.off}', q=query)
    sys.stdout.flush()
    query = dict(Query=('q=' + urllib.parse.quote(query)))
    query = json.dumps(query)
    socket = websocket.WebSocket()
    socket.connect(
        'wss://{host}/instantws'.format(host=host),
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
            colors.print('Results: {n}', n=n_results)
            sys.stdout.flush()
            if n_results == 0:
                break
            packages = wget_json(query_id, 'packages')['Packages']
            colors.print('Packages: {n} ({pkgs})',
                n=len(packages),
                pkgs=' '.join(packages),
            )
            print()
            sys.stdout.flush()
            for n in range(n_pages):
                data = wget_json(query_id, 'page_{n}'.format(n=n))
                print_results(data)
            break
        elif tp == 'pagination':
            n_pages = msg['ResultPages']
        elif tp == 'error':
            if msg['ErrorType'] == 'invalidquery':
                print('DCS error: invalid query')
                sys.exit(1)
            raise NotImplementedError(msg)
        elif tp == 'default':
            continue
        else:
            raise NotImplementedError(msg)

def print_results(items):
    for item in items:
        colors.print('{path}:{line}:', pkg=item['package'], path=item['path'], line=item['line'])
        for line in item['ctxp2'], item['ctxp1']:
            line = html.unescape(line)
            colors.print('{t.dim}|{t.off} {line}', line=line)
        line = html.unescape(item['context'])
        colors.print('{t.dim}>{t.off} {t.bold}{line}{t.off}', line=line)
        for line in item['ctxn1'], item['ctxn2']:
            line = html.unescape(line)
            colors.print('{t.dim}|{t.off} {line}', line=line)
        colors.print('{t.dim}(pathrank {pathrank:.4f}, rank {rank:.4f}){t.off}',
            pathrank=item['pathrank'],
            rank=item['ranking'],
        )
        print()
        sys.stdout.flush()

__all__ = ['main']

# vim:ts=4 sts=4 sw=4 et
