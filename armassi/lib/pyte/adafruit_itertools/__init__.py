# SPDX-FileCopyrightText: 2001-2019 Python Software Foundation
#
# SPDX-License-Identifier: PSF-2.0

"""
`adafruit_itertools`
================================================================================

Python's itertools adapted for CircuitPython by Dave Astels

Copyright 2001-2019 Python Software Foundation; All Rights Reserved

* Author(s): The PSF and Dave Astels

Implementation Notes
--------------------

**Hardware:**

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://github.com/adafruit/circuitpython/releases
"""
# pylint:disable=invalid-name,redefined-builtin,attribute-defined-outside-init
# pylint:disable=stop-iteration-return,anomalous-backslash-in-string

__version__ = "0.0.0+auto.0"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_Itertools.git"


def chain(*iterables):
    """Make an iterator that returns elements from the first iterable until it
    is exhausted, then proceeds to the next iterable, until all of the iterables
    are exhausted. Used for treating consecutive sequences as a single sequence.

    :param p: a list of iterable from which to yield values

    """
    # chain('ABC', 'DEF') --> A B C D E F
    for i in iterables:
        yield from i
