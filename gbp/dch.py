# vim: set fileencoding=utf-8 :
#
# (C) 2010 Rob Browning <rlb@defaultvalue.org>
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""provides git-dch helpers"""

import re

MAX_CHANGELOG_LINE_LENGTH = 76

def extract_git_dch_cmds(lines, options):
    """Return a dictionary of all Git-Dch: commands found in lines.
    The command keys will be lowercased, i.e. {'ignore' : True,
    'short': True}.  For now, all the options are binary.  Also return
    all of the lines that do not contain Git-Dch: commands."""
    commands = {}
    other_lines = []
    for line in lines:
        if line.startswith('Git-Dch: ') or line.startswith('Gbp-Dch: '):
            cmd = line.split(' ', 1)[1].strip().lower()
            commands[cmd] = True
        else:
            other_lines.append(line)
    return (commands, other_lines)


def filter_ignore_rx_matches(lines, options):
    """Filter any lines that match options.ignore_regex
    (i.e. --ignore-regex)."""
    if options.ignore_regex:
        ignore_re = re.compile(options.ignore_regex)
        return [line for line in lines if not ignore_re.match(line)]
    else:
        return lines


_bug_r = r'(?:bug|issue)?\#?\s?\d+'
_bug_re = re.compile(_bug_r, re.I)

def extract_bts_cmds(lines, opts):
    """Return a dictionary of the bug tracking system commands
    contained in the the given lines.  i.e. {'closed' : [1], 'fixed':
    [3, 4]}.  Right now, this will only notice a single directive
    clause on a line.  Also return all of the lines that do not
    contain bug tracking system commands."""
    bts_rx = re.compile(r'(?P<bts>%s):\s+%s' % (opts.meta_closes, _bug_r), re.I)
    commands = {}
    other_lines = []
    for line in lines:
        m = bts_rx.match(line)
        if m:
            bug_nums = [ bug.strip() for bug in _bug_re.findall(line, re.I) ]
            try:
                commands[m.group('bts')] += bug_nums
            except KeyError:
                commands[m.group('bts')] = bug_nums
        else:
            other_lines.append(line)
    return (commands, other_lines)


def extract_thanks_info(lines, options):
    """Return a list of all of the Thanks: entries, and a list of all
    of the lines that do not contain Thanks: entries."""
    thanks = []
    other_lines = []
    for line in lines:
        if line.startswith('Thanks: '):
            thanks.append(line.split(' ', 1)[1].strip())
        else:
            other_lines.append(line)
    return (thanks, other_lines)


def _ispunct(ch):
    return not ch.isalnum() and not ch.isspace()


def terminate_first_line_if_needed(lines):
    """Terminate the first line of lines with a '.' if multi-line."""
    # Don't add a period to empty or one line commit messages.
    if len(lines) < 2:
        return lines
    if lines[0] and _ispunct(lines[0][-1]):
        return lines
    if lines[1] and (_ispunct(lines[1][0]) or lines[1][0].islower()):
        return lines
    return [lines[0] + "."] + lines[1:]


def format_changelog_entry(commit_info, options, last_commit=False):
    """Return a list of lines (without newlines) as the changelog
    entry for commit_info (generated by
    GitRepository.get_commit_info()).  If last_commit is not False,
    then this entry is the last one in the series."""
    entry = [commit_info['subject']]
    body = commit_info['body'].splitlines()
    commitid = commit_info['id']
    (git_dch_cmds, body) = extract_git_dch_cmds(body, options)

    if 'ignore' in git_dch_cmds:
        return None
    if options.idlen:
        entry[0] = '[%s] ' % commitid[0:options.idlen] + entry[0]

    bts_cmds = {}
    thanks  = []
    if options.meta:
        (bts_cmds, body) = extract_bts_cmds(body, options)
        (thanks, body) = extract_thanks_info(body, options)
    body = filter_ignore_rx_matches(body, options)

    if 'full' in git_dch_cmds or (options.full and not 'short' in git_dch_cmds):
        # Add all non-blank body lines.
        entry.extend([line for line in body if line.strip()])
    if thanks:
        # Last wins for now (match old behavior).
        thanks_msg = 'Thanks to %s' % thanks[-1]
        entry.extend([thanks_msg])
    for bts in bts_cmds:
        bts_msg = '(%s: %s)' % (bts, ', '.join(bts_cmds[bts]))
        if len(entry[-1]) + len(bts_msg) >= MAX_CHANGELOG_LINE_LENGTH:
            entry.extend([''])
        else:
            entry[-1] += " "
        entry[-1] += bts_msg

    entry = terminate_first_line_if_needed(entry)
    return entry
