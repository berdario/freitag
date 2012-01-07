#!/usr/bin/env python
# encoding: utf-8
#
# FreiTAG - A simple mp3 command line tool to tag and rename mp3s.
# Copyright (c) 2010-2011 Giuseppe Capizzi
# mailto: g.capizzi@gmail.com
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


import sys
import argparse
from string import replace, Template
from shutil import move
from os import makedirs, sep
from os.path import dirname, join, exists
from re import sub, escape, search

from mutagen.mp3 import EasyMP3


DEFAULT_FORMAT = "%tracknumber - %artist - %title.mp3"
TAGS = [
    {'name': 'album',       'abbr': 'b', 'help': 'The album name'},
    {'name': 'artist',      'abbr': 'a', 'help': 'The artist name'},
    {'name': 'title',       'abbr': 't', 'help': 'The track title'},
    {'name': 'discnumber',  'abbr': 'd', 'help': 'The disc number'},
    {'name': 'tracknumber', 'abbr': 'n', 'help': 'The track number'},
    {'name': 'date',        'abbr': 'y', 'help': 'The track date (year)'}
]


class FormatTemplate(Template):
    delimiter = '%'
    idpattern = '[a-z]+'


class FreiMP3(EasyMP3):
    def __getitem__(self, key):
        value = ''

        try:
            value = super(EasyMP3, self).__getitem__(key)[0]

            # remove the slash and everything after it in track number
            # and zero-pad it
            if key == 'tracknumber':
                value = value.split('/')[0].rjust(2, '0')
        except KeyError:
            pass

        return value


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['get', 'set', 'rename',
                                            'extract', 'humanize'])
    parser.add_argument('files', nargs='+')
    parser.add_argument('--format', '-f', default=DEFAULT_FORMAT,
                        help='The format used by "get", "rename" and '
                        + '"extract" commands. You can use the following '
                        + 'placeholders: '
                        + ', '.join(['%%{0}'.format(t['name']) for t in TAGS]))
    parser.add_argument('--humanize', action="store_true", default=False,
                        help='When extracting, convert all fields from '
                        + 'lowecase_with_underscores format to Capitalized '
                        + 'With Spaces format')

    # tag setters
    for tag in TAGS:
        long_opt = '--%s' % tag['name']
        short_opt = '-%s' % tag['abbr']
        parser.add_argument(long_opt, short_opt, help=tag['help'])

    args = parser.parse_args()

    for filename in args.files:
        mp3 = FreiMP3(filename)

        if args.command == 'get':
            print get(mp3, args.format)
        elif args.command == 'set':
            set(mp3, args)
        elif args.command == 'rename':
            rename(mp3, args.format)
        elif args.command == 'extract':
            extract(mp3, args.format, args.humanize)
        elif args.command == 'humanize':
            humanize(mp3)


def get(mp3, format):
    return FormatTemplate(format).safe_substitute(mp3)


def _unicode(dictionary):
    return dict((name, unicode(value)) for (name, value) in dictionary.items())


def _save(mp3, tags):
    mp3.update(_unicode(tags))
    mp3.save()


def _filter_tags(dictionary):
    tag_names = [tag['name'] for tag in TAGS]
    tags = dict((name, value) for name, value in dictionary.items()
                if name in tag_names and value is not None)


def set(mp3, args):
    _save(mp3, _filter_tags(args.__dict__))


def rename(mp3, format):
    dest = get(mp3, format).strip()

    # create missing directories
    try:
        makedirs(dirname(dest))
    except OSError:
        pass

    if (exists(dest)):
        print "%s already exists! Skipping..." % dest
        return
    else:
        move(mp3.filename, dest)


def _get_regex_for_tag(m):
    tag_name = m.group(1)
    tag_regex = '[^%s]*' % sep

    # non-greedy regex for tracknumber tag
    if tag_name == 'tracknumber':
        tag_regex += '?'

    return '(?P<%(tag_name)s>%(tag_regex)s)' % {'tag_name': tag_name,
                                                'tag_regex': tag_regex}


def _humanize(string):
    return string.replace('_', ' ').capwords()


def _humanize_tags(tags):
    tags_to_humanize = ['album', 'artist', 'title']

    for tag in tags_to_humanize:
        if tags.has_key(tag):
            tags[tag] = _humanize(tags[tag])

    return tags


def _extract(string, format):
    # we need a FormatTemplate instance to get delimiter and idpattern
    t = FormatTemplate('')
    delimiter = t.delimiter
    idpattern = t.idpattern

    # the regex pattern that matches tags in the format string
    # (delimiter must be escaped twice to be successfully substistuted in the
    # next step)
    tag_pattern = '%(del)s(%(pattern)s)' % {'del': escape(escape(delimiter)),
                                            'pattern': idpattern}

    # turn the format string into a regex and parse the filename
    regex = sub(tag_pattern, _get_regex_for_tag, escape(format))
    values = search(regex, string).groupdict()

    return values


def extract(mp3, format, humanize=False):
    tags = _extract(mp3.filename, format)

    # humanize
    if humanize:
        tags = _humanize_tags(tags)

    _save(mp3, tags)


def humanize(mp3):
    _save(mp3, _humanize_tags(tags))


if __name__ == '__main__':
    sys.exit(main())
