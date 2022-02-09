#!/bin/sh

# Copyright © 2022 Jakub Wilk <jwilk@jwilk.net>
# SPDX-License-Identifier: MIT

set -e -u

if [ -z "${DCS_CLI_NETWORK_TESTING-}" ]
then
    echo '1..0 # SKIP set DCS_CLI_NETWORK_TESTING=1 to enable tests that exercise network'
    exit 0
fi

pdir="${0%/*}/.."
prog="$pdir/dcs-cli"

echo 1..1
out=$("$prog" -w '[0-9]*[2-9][1-3]th' filetype:perl)
sed -e 's/^/# /' <<EOF
$out
EOF
echo 'ok 1'

# vim:ts=4 sts=4 sw=4 et ft=sh
