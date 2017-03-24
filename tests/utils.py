# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals
from functools import wraps

import mock


def patch_class_method_with_original(cls, method_name):
    """
    Mock a class method without changing the method return value.
    Useful for patching methods where method arguments have to be
    checked however return value should not be mocked.

    For example:

    class Foo(object):
        def a(self):
            return self.b(123) * 2
        def b(self, arg):
            return arg

    class TestFoo(TestCase):
        @patch_class_method_with_original(Foo, 'b')
        def test_a(self, mock_b):
            foo = Foo()
            actual = foo.a()
            self.assertEqual(actual, 246)
            mock_b.assert_called_once_with(123)

    """
    original_mock = getattr(cls, method_name)

    def outer_wrapper(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            with mock.patch.object(cls, method_name, autospec=True) as mocked:
                mocked.side_effect = original_mock
                new_args = args + (mocked,)
                return f(*new_args, **kwargs)

        return wrapper

    return outer_wrapper
