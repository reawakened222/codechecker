# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

from ..plist_converter import PlistConverter


class PMDPlistConverter(PlistConverter):
    """ PMD plist converter. """

    def _create_diag(self, message, files):
        """ Creates a new plist diagnostic from the given message. """
        diag = super(PMDPlistConverter, self) \
            ._create_diag(message, files)

        return diag
