#
# Copyright (c) 2015-2021 Thierry Florac <tflorac AT ulthar.net>
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#

"""PyAMS_elastic.dotdict module

This module defines a utility class which is used as a dict, but which also allows
dotted access to keys.

When instantiated from a source dict, the source will be crawled recursively to convert
all sub-dicts to this class.
"""

__docformat__ = 'restructuredtext'


class DotDict(dict):
    """A utility class which behaves like a dict, but also allows dot-access to keys"""

    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__

    def __init__(self, d=None):  # pylint: disable=super-init-not-called
        if d is None:
            d = {}
        for key, value in d.items():
            if hasattr(value, 'keys'):
                value = DotDict(value)
            if isinstance(value, list):
                value = [DotDict(el) if hasattr(el, 'keys') else el
                         for el in value]
            self[key] = value

    def __repr__(self):
        return '<%s(%s)>' % (self.__class__.__name__, dict.__repr__(self))
