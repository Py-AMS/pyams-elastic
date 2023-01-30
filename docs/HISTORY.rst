Changelog
=========

1.6.7
-----
 - updated output of Elasticsearch re-indexation task
 - updated tasks docstrings

1.6.6
-----
 - updated translations

1.6.5
-----
 - use pagination and bulk API in Elasticsearch re-indexation task
 - replace 'body' parameter with named arguments

1.6.4
-----
 - restored all unit tests

1.6.3
-----
 - updated unit tests (still partially disabled!)

1.6.2
-----
 - disabled some unit tests because of strange behaviour with Gitlab's Docker

1.6.1
-----
 - updated re-indexation task status on failure

1.6.0
-----
 - added PyAMS scheduler task to handler partial Elasticsearch re-indexation
 - added support for PyAMS dynamic text formatters into Elasticsearch client index name

1.5.2
-----
 - restored deleted services in Gitlab CI configuration

1.5.1
-----
 - use new SQLAlchemy structure to get access to mappings registry
 - added support for Python 3.11

1.5.0
-----
 - allow usage of dynamic text formatters into scheduler Elasticsearch tasks

1.4.1
-----
 - use new scheduler task execution status on failure

1.4.0
-----
 - added certificates management options when creating Elasticsearch client, available in
   Pyramid configuration file

1.3.1
-----
 - updated CI for Python 3.10

1.3.0
-----
 - added SSL settings to client configuration
 - added Elasticsearch update API support
 - allow overriding of configuration file settings with named arguments when creating
   custom Elasticsearch client
 - added support for Python 3.10

1.2.1
-----
 - remove some Elasticsearch (> 7.15) deprecation warnings using named arguments

1.2.0
-----
 - use PyAMS_utils transaction manager

1.1.0
-----
 - updated task add and edit forms title
 - updated package include scan

1.0.0
-----
 - initial release
