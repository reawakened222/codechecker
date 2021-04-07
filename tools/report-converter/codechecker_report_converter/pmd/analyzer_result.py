# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

from codechecker_report_converter.analyzer_result import AnalyzerResult

from .output_parser import PMDParser
from .plist_converter import PMDPlistConverter


class PMDAnalyzerResult(AnalyzerResult):
    """ Transform analyzer result of PMD. """

    TOOL_NAME = 'pmd'
    NAME = 'PMD'
    URL = 'https://pmd.github.io'

    def parse(self, analyzer_result):
        """ Creates plist files from the given analyzer result to the given
        output directory.
        """
        parser = PMDParser()
        messages = parser.parse_messages(analyzer_result)
        if not messages:
            return None

        plist_converter = PMDPlistConverter(self.TOOL_NAME)
        plist_converter.add_messages(messages)
        return plist_converter.get_plist_results()
