==================
Django SubUI Tests
==================

.. image:: https://badge.fury.io/py/django-subui-tests.png
    :target: http://badge.fury.io/py/django-subui-tests

.. image:: https://travis-ci.org/dealertrack/django-subui-tests.png?branch=master
    :target: https://travis-ci.org/dealertrack/django-subui-tests

.. image:: https://coveralls.io/repos/dealertrack/django-subui-tests/badge.png?branch=master
    :target: https://coveralls.io/r/dealertrack/django-subui-tests?branch=master

Framework to make workflow server integration test suites

* Free software: MIT license
* GitHub: https://github.com/dealertrack/django-subui-tests
* Documentation: http://django-subui-tests.readthedocs.io/

Installing
----------

You can install ``django-subui-tests`` using pip::

    $ pip install django-subui-tests

Testing
-------

To run the tests you need to install testing requirements first::

    $ make install

Then to run tests, you can use ``nosetests`` or simply use Makefile command::

    $ nosetests -sv
    # or
    $ make test
