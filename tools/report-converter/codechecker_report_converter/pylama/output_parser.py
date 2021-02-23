# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

import logging
import os
import re

from ..output_parser import Message, BaseParser

LOG = logging.getLogger('ReportConverter')


class PylamaParser(BaseParser):
    """ Parser for Pyflakes output. """

    def __init__(self, analyzer_result):
        super(PylamaParser, self).__init__()

        self.analyzer_result = analyzer_result

        # Regex for parsing pylama's parsable format.
        self.message_line_re = re.compile(
            # File path followed by a ':'.
            r'^(?P<path>[\S ]+?):'
            # Line number followed by a ':'.
            r'(?P<line>\d+?):'
            # Column number followed by a ':'.
            r'(?P<column>\d+?):'
            # Severity level, uppercase letter within brackets.
            r'\s\[(?P<severity>[A-Z])\]\s*'
            # Message.
            r'(?P<message>[\S \t]+)\s*\[(?P<checker>[^]])\]\s$')

    def severity_mapper(severityChar):
        return "unknown"

    def parse_message(self, it, line):
        """Parse the given line.

        Returns a (message, next_line) pair or throws a StopIteration.
        The message could be None.
        """
        match = self.message_line_re.match(line)
        if match is None:
            return None, next(it)

        file_path = os.path.join(os.path.dirname(self.analyzer_result),
                                 match.group('path'))

        severity = f"[{match.group('severity')}]"
        message = Message(
            file_path,
            int(match.group('line')),
            int(match.group('column')),
            f"{severity} {match.group('message').strip()}",
            match.group('checker'))

        try:
            return message, next(it)
        except StopIteration:
            return message, ''
