from __future__ import print_function, unicode_literals
from unittest import TestCase

import mock
from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import Resolver404
from django.http.response import HttpResponse
from django.template.response import SimpleTemplateResponse

from subui.validators import (
    BaseValidator,
    FormInitialDataValidator,
    HeaderValidator,
    RedirectToRouteValidator,
    ResponseContentContainsValidator,
    ResponseContentNotContainsValidator,
    SessionDataValidator,
    StatusCodeValidator,
)


TESTING_MODULE = 'subui.validators'


class TestBaseValidator(TestCase):
    def setUp(self):
        class Validator(BaseValidator):
            pass

        self.validator_class = Validator

    def test_init(self):
        """
        Test that __init__ properly stores given parameters
        """
        mock_step = mock.MagicMock(test=mock.create_autospec(self))
        kwargs = {
            'hello': 'world',
            'foo': 'bar',
        }

        self.validator_class.hello = 'mars'
        validator = self.validator_class(mock_step, **kwargs)

        self.assertIs(validator.step, mock_step)
        for key, value in kwargs.items():
            self.assertTrue(hasattr(validator, key))
            self.assertEqual(getattr(validator, key), value)

    def test_get_expected_attrs(self):
        """
        Test that _get_expected_attrs returns expected attributes
        from all base classes.
        """

        class Validator(BaseValidator):
            expected_attrs = ('foo1',)

        class Validator2(Validator):
            expected_attrs = ('foo2',)

        class Validator3(Validator):
            expected_attrs = ('foo3',)

        class Validator4(Validator2, Validator3):
            expected_attrs = ('foo4',)

        validator = Validator4()

        self.assertSetEqual(set(validator._get_expected_attrs()),
                            {'foo1', 'foo2', 'foo3', 'foo4'})

    def test_check_importper_configuration(self):
        """
        Test that _check_improper_configuration verifies
        that all expected attributes are defined.
        """
        self.validator_class.expected_attrs = ('foo',)
        validator = self.validator_class()

        with self.assertRaises(ImproperlyConfigured):
            validator._check_improper_configuration()

        validator.foo = 'bar'
        validator._check_improper_configuration()

        self.assertTrue(True)

    @mock.patch.object(BaseValidator, '_check_improper_configuration')
    def test_test(self, mock_check_improper_configuration):
        """
        Test that test sets the test step and calls the
        _check_improper_configuration
        """
        validator = self.validator_class()
        mock_step = mock.MagicMock(test=mock.create_autospec(self))

        validator.test(mock_step)

        self.assertIs(validator.step, mock_step)
        mock_check_improper_configuration.assert_called_once_with()


class TestHeaderValidator(TestCase):
    def setUp(self):
        self.validator = HeaderValidator()

    def test_get_expected_attrs(self):
        """
        Test that _get_expected_attrs accounts value of
        test_header_value attribute
        """
        self.assertSetEqual(set(self.validator._get_expected_attrs()),
                            {'header_name', 'expected_header'})

        self.validator.test_header_value = False
        self.assertSetEqual(set(self.validator._get_expected_attrs()),
                            {'header_name'})

    def test_test(self):
        """
        Test that expected header is present in the response
        and its value is validated when test_header_value is True
        """
        self.validator.test_header_value = False
        self.validator.header_name = 'header-name'
        self.validator.expected_header = 'some-value'

        self.validator.step = mock_step = mock.Mock(test=mock.create_autospec(self))
        self.validator.step.response = {'header-name': 'header-name'}
        self.validator.step.test = mock.Mock(unsafe=True)

        self.validator.test(mock_step)

        mock_step.test.assertIn.assert_called_once_with(
            'header-name',
            mock_step.response,
            mock.ANY
        )
        self.assertFalse(mock_step.test.assertEqual.called)

        self.validator.test_header_value = True
        mock_step.test.reset_mock()
        self.validator.test(mock_step)

        mock_step.test.assertEqual.assert_called_once_with(
            mock_step.response['header-name'],
            'some-value',
            mock.ANY
        )

        self.validator.test_contains_value = True
        mock_step.test.reset_mock()
        self.validator.test(mock_step)

        self.assertFalse(self.validator.test_header_value)
        mock_step.test.assertIn.assert_has_calls([
            mock.call('header-name',
                      mock_step.response,
                      mock.ANY),
            mock.call('some-value',
                      mock_step.response['header-name'],
                      mock.ANY)
        ])
        self.assertFalse(mock_step.test.assertEqual.called)


class TestStatusCodeValidator(TestCase):
    def setUp(self):
        self.validator = StatusCodeValidator()

    def test_test(self):
        """
        Test that the validator is testing status code of the response
        """
        self.validator.expected_status_code = 200

        mock_step = mock.MagicMock(test=mock.create_autospec(self))
        mock_step.test = mock.Mock(unsafe=True)

        self.validator.test(mock_step)

        mock_step.test.assertEqual.assert_called_once_with(
            mock_step.response.status_code,
            200,
            mock.ANY
        )


class TestRedirectToRouteValidator(TestCase):
    def setUp(self):
        self.validator = RedirectToRouteValidator()

    @mock.patch(TESTING_MODULE + '.resolve')
    def test_test(self, mock_resolve):
        """
        Check that test verified that the response redirects
        to a particular route name
        """
        self.validator.expected_route_name = 'some-route'
        response = HttpResponse('', status=302)
        response['Location'] = 'http://example.com/foo/bar/?query=here#fragment'

        mock_step = mock.MagicMock(
            test=mock.create_autospec(self),
            response=response,
        )
        mock_resolve.return_value.view_name = 'view-name'

        self.validator.test(mock_step)

        mock_step.test.assertEqual.assert_any_call(
            'view-name',
            'some-route',
            mock.ANY
        )
        mock_resolve.assert_called_once_with('/foo/bar/')

    @mock.patch(TESTING_MODULE + '.resolve')
    def test_test_invalid(self, mock_resolve):
        """
        Check that test verified that the response redirects
        to a particular route name when the redirect path
        cannot be resolved by Django
        """
        self.validator.expected_route_name = 'some-route'
        response = HttpResponse('', status=302)
        response['Location'] = 'http://example.com/foo/bar/?query=here#fragment'

        mock_step = mock.MagicMock(
            test=mock.create_autospec(self),
            response=response,
        )
        mock_resolve.side_effect = Resolver404
        mock_step.test.fail.side_effect = RuntimeError

        with self.assertRaises(RuntimeError):
            self.validator.test(mock_step)

        mock_step.test.fail.assert_called_once_with(mock.ANY)
        mock_resolve.assert_called_once_with('/foo/bar/')


class TestResponseContentContainsValidator(TestCase):
    def setUp(self):
        self.validator = ResponseContentContainsValidator()

    def test_test(self):
        self.validator.expected_content = 'some content'

        mock_step = mock.MagicMock(
            response=mock.MagicMock(
                content=b'abc',
            ),
            test=mock.create_autospec(self),
        )

        self.validator.test(mock_step)

        mock_step.test.assertIn.assert_any_call(
            'some content',
            'abc',
            mock.ANY
        )


class TestResponseContentNotContainsValidator(TestCase):
    def setUp(self):
        self.validator = ResponseContentNotContainsValidator()

    def test_test(self):
        self.validator.unexpected_content = 'some content'

        mock_step = mock.MagicMock(
            response=mock.MagicMock(
                content=b'abc',
            ),
            test=mock.create_autospec(self),
        )

        self.validator.test(mock_step)

        mock_step.test.assertNotIn.assert_any_call(
            'some content',
            'abc',
            mock.ANY
        )


class TestSessionDataValidator(TestCase):
    def setUp(self):
        self.validator = SessionDataValidator()

    def test_test(self):
        self.validator.expected_session_key = 'foo'
        self.validator.expected_session_secondary_keys = ['bar']
        session = {
            'foo': {
                'bar': 'value',
            },
        }

        mock_step = mock.Mock(
            response=mock.Mock(
                wsgi_request=mock.Mock(
                    session=session,
                ),
            ),
            test=mock.create_autospec(self),
        )

        self.validator.test(mock_step)

        mock_step.test.assertIn.assert_has_calls([
            mock.call('foo',
                      session.keys(),
                      mock.ANY),
            mock.call('bar',
                      session['foo'].keys(),
                      mock.ANY)
        ])
        mock_step.test.assertIsInstance.assert_called_once_with(
            session['foo'],
            dict,
            mock.ANY
        )
        mock_step.test.assertIsNotNone.assert_called_once_with(
            session['foo']['bar'],
            mock.ANY
        )


class TestFormInitialDataValidator(TestCase):
    def setUp(self):
        self.validator = FormInitialDataValidator()

    def test_test(self):
        self.validator.test_initial_value = True
        self.validator.initial_data_key = 'foo'
        self.validator.expected_initial_data_value = 'bar'

        initial = {
            'foo': 'value',
        }
        mock_step = mock.Mock(
            response=mock.Mock(
                spec=SimpleTemplateResponse,
                context_data={
                    'form': mock.Mock(
                        initial=initial,
                    )
                }
            ),
            test=mock.create_autospec(self),
        )

        self.validator.test(mock_step)

        mock_step.test.assertIsInstance.assert_has_calls([
            mock.call(mock_step.response,
                      SimpleTemplateResponse,
                      mock.ANY),
            mock.call(initial,
                      dict,
                      mock.ANY, )
        ])
        mock_step.test.assertIn.assert_has_calls([
            mock.call('form',
                      mock_step.response.context_data,
                      mock.ANY),
            mock.call('foo',
                      initial.keys(),
                      mock.ANY),
        ])
        mock_step.test.assertIsNotNone.assert_called_once_with(
            'value',
            mock.ANY,
        )
        mock_step.test.assertEqual.assert_called_once_with(
            'value',
            'bar',
            mock.ANY,
        )
