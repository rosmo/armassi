"""
    pyte.charsets
    ~~~~~~~~~~~~~

    This module defines ``G0`` and ``G1`` charset mappings the same way
    they are defined for linux terminal, see
    ``linux/drivers/tty/consolemap.c`` @ http://git.kernel.org

    .. note:: ``VT100_MAP`` and ``IBMPC_MAP`` were taken unchanged
              from linux kernel source and therefore are licensed
              under **GPL**.

    :copyright: (c) 2011-2012 by Selectel.
    :copyright: (c) 2012-2017 by pyte authors and contributors,
                    see AUTHORS for details.
    :license: LGPL, see LICENSE for more details.
"""

#: Latin1.
# LAT1_MAP = "".join(map(chr, range(256)))

MAPS = {
}
