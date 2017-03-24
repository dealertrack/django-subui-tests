from __future__ import print_function, unicode_literals
from collections import OrderedDict
from unittest import TestCase

import mock
from pycontext.context import Context

from subui.test_runner import SubUITestRunner


TESTING_MODULE = 'subui.test_runner'


class TestSubUITestRunner(TestCase):
    @mock.patch.object(SubUITestRunner, '_normalize_steps')
    def test_init(self, mock_normalize_steps):
        """
        Test that init correctly handles input parameters
        """
        runner = SubUITestRunner(steps=[],
                                 client=mock.sentinel.client,
                                 state={'hello': 'world'})

        self.assertEqual(runner.steps, [])
        self.assertEqual(runner.client, mock.sentinel.client)
        self.assertIsInstance(runner.state, Context)
        self.assertEqual(runner.state, {'hello': 'world'})
        mock_normalize_steps.assert_called_once_with()

        with self.assertRaises(AssertionError):
            SubUITestRunner(steps=None, client=None)

    @mock.patch('inspect.isclass')
    def test_normalize_keys(self, mock_isclass):
        """
        Test that _normalize_steps converts steps to OrderedDict
        and instantiated each step if necessary
        """
        mock_isclass.side_effect = True, False
        step1 = mock.MagicMock()
        step2 = mock.MagicMock()

        with mock.patch.object(SubUITestRunner, '_normalize_steps'):
            runner = SubUITestRunner([step1, step2],
                                     None,
                                     something='here',
                                     morestuff='here')

        self.assertNotIsInstance(runner.steps, OrderedDict)

        runner._normalize_steps()

        step1.assert_called_once_with(something='here', morestuff='here')
        self.assertFalse(step2.called)

        self.assertIsInstance(runner.steps, OrderedDict)
        self.assertEqual(runner.steps, OrderedDict((
            (0, step1()),
            (1, step2),
        )))

    def test_run(self):
        """
        Test that run loops all steps and executes them
        """
        step = mock.MagicMock()
        runner = SubUITestRunner([step], None)

        actual = runner.run()

        self.assertIs(actual, runner)
        step.init.assert_called_once_with(
            client=runner.client,
            steps=runner.steps,
            step_index=0,
            step_key=0,
            state=runner.state
        )
        step.request.assert_called_once_with()
        step.test_response.assert_called_once_with()
