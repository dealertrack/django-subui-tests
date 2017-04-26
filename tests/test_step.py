from __future__ import print_function, unicode_literals
from collections import OrderedDict
from unittest import TestCase

import mock
import six

from subui.step import StatefulUrlParamsTestStep, TestStep

from .utils import patch_class_method_with_original


TESTING_MODULE = 'subui.step'


class TestTestStep(TestCase):
    def test__init__(self):
        """
        Test that __init__ overwrites attributes with
        given parameters
        """
        step = TestStep(hello='world')
        self.assertTrue(hasattr(step, 'hello'))
        self.assertEqual(getattr(step, 'hello'), 'world')

    def test_init(self):
        """
        Test that init stores given parameters as attributes
        """
        step = TestStep()
        step.init(mock.sentinel.client,
                  mock.sentinel.steps,
                  mock.sentinel.step_index,
                  mock.sentinel.step_key,
                  mock.sentinel.state)

        self.assertEqual(step.client, mock.sentinel.client)
        self.assertEqual(step.steps, mock.sentinel.steps)
        self.assertEqual(step.step_index, mock.sentinel.step_index)
        self.assertEqual(step.step_key, mock.sentinel.step_key)
        self.assertEqual(step.state, mock.sentinel.state)

    def test_steps(self):
        """
        Test prev_steps, next_steps, prev_step and next_step
        properties
        """
        step = TestStep()
        step.steps = OrderedDict((
            ('one', 1),
            ('two', 2),
            ('three', 3),
            ('four', 4),
            ('five', 5),
        ))
        step.step_index = 2

        self.assertEqual(
            step.prev_steps,
            OrderedDict((
                ('two', 2),
                ('one', 1),
            ))
        )
        self.assertEqual(
            step.prev_step,
            2,
        )
        self.assertEqual(
            step.next_step,
            4,
        )

    def test_get_content_type(self):
        """
        Test that get_content_type returns content_type if defined
        """
        step = TestStep()
        self.assertEqual(step.get_content_type(), '')

        step.content_type = 'application/json'
        self.assertEqual(step.get_content_type(), 'application/json')

    def test_get_override_settings(self):
        """
        Test that get_override_settings returns overriden_settings if defined
        """
        step = TestStep()
        self.assertDictEqual(step.get_override_settings(), {})

        step.overriden_settings = {
            'ROOT_URLCONF': 'services.urls'
        }
        self.assertEqual(step.get_override_settings(), {'ROOT_URLCONF': 'services.urls'})

    def test_get_urlconf(self):
        """
        Test that get_urlconf returns urlconf  if defined
        """
        step = TestStep()
        self.assertIsNone(step.get_urlconf())

        step.urlconf = 'services.urls'
        self.assertEqual(step.get_urlconf(), 'services.urls')

    def test_get_url_args(self):
        """
        Test that get_url_args returns url args if defined
        """
        step = TestStep()
        self.assertTupleEqual(step.get_url_args(), tuple())

        step.url_args = ('foo',)
        self.assertTupleEqual(step.get_url_args(), ('foo',))

    def test_get_url_kwargs(self):
        """
        Test that get_url_kwargs returns url kwargs if defined
        """
        step = TestStep()
        self.assertDictEqual(step.get_url_kwargs(), {})

        step.url_kwargs = {'foo': 'bar'}
        self.assertDictEqual(step.get_url_kwargs(), {'foo': 'bar'})

    @patch_class_method_with_original(TestStep, 'get_url_kwargs')
    @patch_class_method_with_original(TestStep, 'get_url_args')
    @mock.patch(TESTING_MODULE + '.reverse')
    def test_get_url(self,
                     mock_get_url_args,
                     mock_get_url_kwargs,
                     mock_reverse):
        mock_reverse.return_value = mock.sentinel.reverse

        step = TestStep()
        step.url_name = 'url-name'
        actual = step.get_url()

        self.assertEqual(actual, mock.sentinel.reverse)
        mock_get_url_args.assert_called_once_with(step)
        mock_get_url_kwargs.assert_called_once_with(step)
        mock_reverse.assert_called_once_with(
            'url-name', args=tuple(), urlconf=None, kwargs={})

    def test_get_request_data(self):
        """
        Test that get_request_data returns data if defined
        """
        step = TestStep()
        actual = step.get_request_data()
        self.assertEqual(actual, {})

        step.data = {'hello': 'world'}
        actual = step.get_request_data()
        self.assertEqual(actual, {'hello': 'world'})

        actual = step.get_request_data({'foo': 'bar'})
        self.assertEqual(actual, {'foo': 'bar'})

    def test_get_validators(self):
        """
        Test that get_validators returns validators
        """
        step = TestStep()
        step.validators = mock.sentinel.validators
        self.assertEqual(step.get_validators(), mock.sentinel.validators)

    @patch_class_method_with_original(TestStep, 'post_request_hook')
    @patch_class_method_with_original(TestStep, 'pre_request_hook')
    @mock.patch.object(TestStep, 'get_url')
    def test_request(self,
                     mock_pre_request_hook,
                     mock_post_response_hook,
                     mock_get_url):
        """
        Test that request correctly calls the client
        """
        mock_client = mock.MagicMock()
        mock_client.methodname.return_value = mock.sentinel.response
        mock_get_url.return_value = mock.sentinel.url

        step = TestStep(client=mock_client, data={'hello': 'world'})
        step.request_method = 'methodname'

        actual = step.request()

        self.assertEqual(actual, mock.sentinel.response)
        mock_pre_request_hook.assert_called_once_with(step)
        mock_post_response_hook.assert_called_once_with(step)

    @mock.patch.object(TestStep, 'get_url')
    def test_request_with_error(self, mock_get_url):
        """
        Test that request exceptions are handled correctly
        """
        mock_client = mock.MagicMock()
        mock_client.methodname.side_effect = ValueError
        mock_get_url.return_value = mock.sentinel.url

        step = TestStep(client=mock_client, step_key='foo', data={'hello': 'world'})
        step.request_method = 'methodname'

        with self.assertRaises(Exception) as e:
            step.request()

        self.assertEqual(e.exception.__class__.__name__, 'ValueError')
        self.assertEqual(
            six.text_type(e.exception).splitlines()[0],
            'Response for {foo:TestStep} requesting "sentinel.url" failed:'
        )

    @patch_class_method_with_original(TestStep, 'post_test_response')
    @patch_class_method_with_original(TestStep, 'pre_test_response')
    @mock.patch('inspect.isclass')
    def test_test_response(self,
                           mock_pre_test_response,
                           mock_post_test_response,
                           mock_isclass):
        """
        Test that test_response loops over all validators
        and correctly calls them
        """
        mock_isclass.side_effect = [True, False]
        validator = mock.MagicMock()
        class_validator = mock.MagicMock()
        step = TestStep(validators=[class_validator, validator])
        step.test_response()

        validator.test.assert_called_once_with(step)
        class_validator.assert_called_once_with(step)
        class_validator().test.assert_called_once_with(step)
        mock_pre_test_response.assert_called_once_with(step)
        mock_post_test_response.assert_called_once_with(step)


class TestStatefulUrlParamsTestStep(TestCase):
    @mock.patch.object(TestStep, 'get_url_args')
    def test_get_url_args(self, mock_get_url_args):
        """
        Test that get_url_args returns args from the state if present
        """
        mock_get_url_args.return_value = mock.sentinel.super
        mock_state = mock.MagicMock()
        mock_state.get.return_value = mock.sentinel.args

        step = StatefulUrlParamsTestStep(state=mock_state)
        actual = step.get_url_args()

        self.assertEqual(actual, mock.sentinel.args)
        mock_state.get.assert_called_once_with('url_args', mock.sentinel.super)

    @mock.patch.object(TestStep, 'get_url_kwargs')
    def test_get_url_kwargs(self, mock_get_url_kwargs):
        """
        Test that get_url_args returns kwargs from the state if present
        """
        mock_get_url_kwargs.return_value = mock.sentinel.super
        mock_state = mock.MagicMock()
        mock_state.get.return_value = mock.sentinel.kwargs

        step = StatefulUrlParamsTestStep(state=mock_state)
        actual = step.get_url_kwargs()

        self.assertEqual(actual, mock.sentinel.kwargs)
        mock_state.get.assert_called_once_with('url_kwargs', mock.sentinel.super)

    @mock.patch.object(TestStep, 'get_url')
    def test_get_request_kwargs(self, mock_get_url):
        """
        Test that get_request_kwargs returns correct kwargs
        """
        step = TestStep(
            data={'foo': 'bar'},
            content_type='application/json'
        )
        self.assertDictEqual(
            step.get_request_kwargs(), {
                'path': mock_get_url.return_value,
                'data': {'foo': 'bar'},
                'content_type': 'application/json'
            }
        )
