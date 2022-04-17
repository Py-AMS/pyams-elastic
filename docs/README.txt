=====================
PyAMS elastic package
=====================

.. contents::


What is PyAMS?
==============

PyAMS (Pyramid Application Management Suite) is a small suite of packages written for applications
and content management with the Pyramid framework.

**PyAMS** is actually mainly used to manage web sites through content management applications (CMS,
see PyAMS_content package), but many features are generic and can be used inside any kind of web
application.

All PyAMS documentation is available on `ReadTheDocs <https://pyams.readthedocs.io>`_; source code
is available on `Gitlab <https://gitlab.com/pyams>`_ and pushed to `Github
<https://github.com/py-ams>`_. Doctests are available in the *doctests* source folder.


What is PyAMS elastic?
======================

PyAMS_elastic is an extension package for PyAMS to provide support for Elasticsearch; it's a fork
of *pyramid_es* package, adapted to use last Elasticsearch features and Elasticsearch-DSL package
(see `Elasticsearch <https://elasticsearch-py.readthedocs.io>` and `Elasticsearch-DSL
<https://elasticsearch-dsl.readthedocs.io>`). It is also using more components of the components
architecture.

Compared with *pyramid_es*, it's no more Python 2 compliant, and adds a few features like
aggregations support in Elasticsearch queries. Deprecated Elasticsearch features have also been
removed from package.

A PyAMS scheduler task info is also provided by this package; it allows running Elasticsearch
queries on a regular basis, and to send notifications if expected results are not received.


Running PyAMS_elastic unit tests
================================

Unit tests relies on an "elasticsearch" entry to be used with Gitlab-CI services. If you want to
run unit tests locally, you must have an entry in your "hosts" file pointing to your Elasticsearch
server.
