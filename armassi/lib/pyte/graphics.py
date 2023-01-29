"""
    pyte.graphics
    ~~~~~~~~~~~~~

    This module defines graphic-related constants, mostly taken from
    :manpage:`console_codes(4)` and
    http://pueblo.sourceforge.net/doc/manual/ansi_color_codes.html.

    :copyright: (c) 2011-2012 by Selectel.
    :copyright: (c) 2012-2017 by pyte authors and contributors,
                    see AUTHORS for details.
    :license: LGPL, see LICENSE for more details.
"""

#: A mapping of ANSI text style codes to style names, "+" means the:
#: attribute is set, "-" -- reset; example:
#:
#: >>> text[1]
#: '+bold'
#: >>> text[9]
#: '+strikethrough'
TEXT = {
    1: "+bold",
#    3: "+italics",
#    4: "+underscore",
    5: "+blink",
    7: "+reverse",
#    9: "+strikethrough",
    22: "-bold",
#    23: "-italics",
#    24: "-underscore",
    25: "-blink",
    27: "-reverse",
#    29: "-strikethrough",
}

#: A mapping of ANSI foreground color codes to color names.
#:
#: >>> FG_ANSI[30]
#: 'black'
#: >>> FG_ANSI[38]
#: 'default'
FG_ANSI = {
    30: 0,
    31: 2,
    32: 3,
    33: 4,
    34: 5,
    35: 6,
    36: 7,
    37: 1,
    39: 1  # white.
}

#: An alias to :data:`~pyte.graphics.FG_ANSI` for compatibility.
FG = FG_ANSI

#: A mapping of non-standard ``aixterm`` foreground color codes to
#: color names. These are high intensity colors.
FG_AIXTERM = {
    90: 8,
    91: 10,
    92: 11,
    93: 12,
    94: 13,
    95: 14,
    96: 15,
    97: 9
}

#: A mapping of ANSI background color codes to color names.
#:
#: >>> BG_ANSI[40]
#: 'black'
#: >>> BG_ANSI[48]
#: 'default'
BG_ANSI = {
    40: 0,
    41: 2,
    42: 3,
    43: 4,
    44: 5,
    45: 6,
    46: 7,
    47: 1,
    49: 0  # black.
}

#: An alias to :data:`~pyte.graphics.BG_ANSI` for compatibility.
BG = BG_ANSI

#: A mapping of non-standard ``aixterm`` background color codes to
#: color names. These are high intensity colors.
BG_AIXTERM = {
    100: 8,
    101: 10,
    102: 11,
    103: 12,
    104: 13,
    105: 14,
    106: 15,
    107: 9
}

