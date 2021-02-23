# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

from codechecker_report_converter.analyzer_result import AnalyzerResult

from .output_parser import KernelDocParser
from ..plist_converter import PlistConverter


class KernelDocAnalyzerResult(AnalyzerResult):
    """ Transform analyzer result of kernel-docs. """

    TOOL_NAME = 'kernel-doc'
    NAME = 'Kernel-Doc'
    URL = 'https://github.com/torvalds/linux/blob/master/scripts/kernel-doc'

    def parse(self, analyzer_result):
        """ Creates plist files from the given analyzer result to the given
        output directory.
        """
        parser = KernelDocParser(analyzer_result)

        content = self._get_analyzer_result_file_content(analyzer_result)
        if not content:
            return

        messages = parser.parse_messages(content)

        plist_converter = PlistConverter(self.TOOL_NAME)
        plist_converter.add_messages(messages)
        return plist_converter.get_plist_results()
