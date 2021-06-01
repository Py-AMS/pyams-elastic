=====================
PyAMS elastic package
=====================

Introduction
------------

This package is composed of a set of utility functions, usable into any Pyramid application.

    >>> from pyramid.testing import setUp, tearDown
    >>> config = setUp(hook_zca=True)

    >>> from cornice import includeme as include_cornice
    >>> include_cornice(config)
    >>> from pyams_utils import includeme as include_utils
    >>> include_utils(config)
    >>> from pyams_elastic import includeme as include_elastic
    >>> include_elastic(config)


    >>> tearDown()
