from __future__ import print_function, unicode_literals
import inspect
import sys
import unittest
from collections import OrderedDict

import six
from django.core.urlresolvers import reverse

from .validators import BaseValidator


class TestStep(object):
    """
    Test step for :py:class:`subui.test_runner.SubUITestRunner`.

    The step is responsible for executing a self-contained task
    such as submitting a form to a particular URL and then
    make assertions regarding the server response.

    :var unittest.TestCase TestStep.test: Test class instance
        with which validators are going to run all their
        assertions with. By default it is an instance of
        :py:class:`unittest.TestCase` however can be changed
        to any other class to add additional assertion methods.
    :var str url_name: Name of the url as defined in ``urls.py``
        by which the URL is going to be calculated.
    :var tuple url_args: URL args to be used while calculating
        the URL using Django's ``reverse``.
    :var dict url_kwargs: URL kwargs to be used while calculating
        the URL using Django's ``reverse``.
    :var str request_method: HTTP method to use for the request.
        Default is ``"post"``
    :var dict data: Data to be sent to the server in the request
    :var platform_utils.utils.dt_context.BaseContext state:
        Reference to a global state from the test runner.
    :var list TestStep.validators: List of response validators
    :var response: Server response for the made request.
        This attribute is only available after
        :py:meth:`request` is called.

    :param kwargs: A dictionary of values which will overwrite
        any instance attributes. This allows to pass additional
        data to the test step without necessarily subclassing
        and manually instantiating step instance.
    :type kwargs: dict
    """
    test = unittest.TestCase('__init__')

    url_name = None
    url_args = None
    url_kwargs = None

    request_method = 'post'

    state = None
    data = None

    validators = []

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def init(self, client, steps, step_index, step_key, state):
        """
        Initialize the step with necessary values from the
        test runner.

        :param client: Django test client to use to make server requests
        :type client: django.test.client.Client

        :param steps: All steps from the test runner.
            This and step index allows to get previous and/or
            next steps.
        :type steps: collections.OrderedDict

        :param step_index: Index of the step within all steps
            test runner will execute.
        :type step_index: int

        :param step_key: Key of the state of how it was provided
            to the test runner in case test step needs
            to reference other steps within the runner by their.
        :type step_key: str

        :param state: Global state reference from the test runner.
        :type state: platform_utils.utils.dt_context.BaseContext
        """
        self.client = client
        self.steps = steps
        self.step_index = step_index
        self.step_key = step_key

        self.state = state

    @property
    def prev_steps(self):
        """
        Get :py:class:`collections.OrderedDict` of previous steps
        excluding itself, if any.

        .. note:: The steps are returned in order of adjacency
            from the current step. For example
            (using list instead of OrederedDict in example)::

                > step = TestStep()
                > step.steps = [0, 1, 2, 3, 4]
                > step.step_index = 3
                > step.prev_steps
                [2, 1, 0]

        :rtype: :py:class:`collections.OrderedDict`
        """
        return OrderedDict(list(self.steps.items())[:self.step_index][::-1])

    @property
    def next_steps(self):
        """
        Get :py:class:`collections.OrderedDict` of next steps
        excluding itself, if any.

        :rtype: :py:class:`collections.OrderedDict`
        """
        return OrderedDict(list(self.steps.items())[self.step_index + 1:])

    @property
    def prev_step(self):
        """
        Get previous step instance, if any.

        :rtype: :py:class:`TestStep`
        """
        prev_steps = list(self.prev_steps.values())
        return prev_steps[0] if prev_steps else None

    @property
    def next_step(self):
        """
        Get previous step instance, if any.

        :rtype: :py:class:`TestStep`
        """
        next_steps = list(self.next_steps.values())
        return next_steps[0] if next_steps else None

    def get_url_args(self):
        """
        Get ``url_args`` which will be used to compute
        the URL using ``reverse``.

        By default this returns :py:attr:`url_args`, if defined,
        else empty tuple.

        :rtype: tuple
        """
        return self.url_args or tuple()

    def get_url_kwargs(self):
        """
        Get ``url_kwargs`` which will be used to compute
        the URL using ``reverse``.

        By default this returns :py:attr:`url_kwargs`, if defined,
        else empty dict.

        :rtype: dict
        """
        return self.url_kwargs or {}

    def get_url(self):
        """
        Compute the URL to request using Django's ``reverse``.

        Reverse is called using :py:attr:`url_name`,
        :py:meth:`get_url_args` and :py:meth:`get_url_args`.

        :rtype: str
        """
        return reverse(self.url_name,
                       args=self.get_url_args(),
                       kwargs=self.get_url_kwargs())

    def get_request_data(self, data=None):
        """
        Get data dict to be sent to the server.

        :param data: Data to be used while sending server request.
            If not defined, :py:attr:`data` is returned.

        :rtype: dict
        """
        return (self.data if data is None else data) or {}

    def get_request_kwargs(self):
        """
        Get kwargs to be passed to the :py:attr:`client`.

        By default this returns dict of format::

            {
                'path': ...,
                'data': ...
            }

        Can be overwritten in case additional parameters need
        to be passed to the client to make the request.

        :rtype: dict
        """
        return {
            'path': self.get_url(),
            'data': self.get_request_data(),
        }

    def get_validators(self):
        """
        Get all validators.

        By default returns :py:attr:`validators` however
        can be used as a hook to returns additional validators
        dynamically.

        :rtype: list
        """
        return self.validators

    def request(self):
        """
        Make the server request. Server response is then saved
        in :py:attr:`request`.

        Before making the request, :py:meth:`pre_request_hook`
        is called and :py:meth:`post_request_hook` is called
        after the request.

        :returns: server response
        """
        self.pre_request_hook()
        try:
            self.response = (getattr(self.client, self.request_method)
                             (**self.get_request_kwargs()))
        except Exception:
            validator = BaseValidator(self)
            e_type, e, e_traceback = sys.exc_info()

            msg = ('{} failed:\n\n{}'
                   ''.format(validator._get_base_error_message(),
                             six.text_type(e)))

            cls = type(e_type.__name__, (Exception,), {})
            six.reraise(
                cls,
                cls(msg),
                e_traceback
            )

        self.post_request_hook()

        return self.response

    def test_response(self):
        """
        Test the server response by looping over all
        validators as returned by :py:meth:`get_validators`.

        Before assertions, :py:meth:`pre_test_response`
        is called and :py:meth:`post_test_response` is called
        after assertions.
        """
        self.pre_test_response()

        for validator in self.get_validators():
            if inspect.isclass(validator):
                validator(self).test(self)
            else:
                validator.test(self)

        self.post_test_response()

    def pre_test_response(self):
        """
        Hook which is executed before validating the response.
        """
        pass

    def post_test_response(self):
        """
        Hook which is executed after validating the response.
        """
        pass

    def pre_request_hook(self):
        """
        Hook which is executed before server request is sent.
        """
        pass

    def post_request_hook(self):
        """
        Hook which is executed after server request is sent.
        """
        pass


class StatefulUrlParamsTestStep(TestStep):

    """
    Test step same as :py:class:`TestStep`
    except it references ``url_args`` and ``url_kwargs`` from the state.

    Having url computed from the state, allows for a particular step
    to change ``url_args`` or ``url_kwargs`` hence future
    steps will fetch different resources.
    """

    def get_url_args(self):
        """
        Get URL args for Django's ``reverse``

        Similar to :py:meth:`TestStep.get_url_args` except
        url args are retrieved by default from state and if not
        available get args from class attribute.

        :returns: tuple of url_args
        """
        args = super(StatefulUrlParamsTestStep, self).get_url_args()
        return self.state.get('url_args', args)

    def get_url_kwargs(self):
        """
        Get URL kwargs fpr Django's ``reverse``

        Similar to :py:meth:`TestStep.get_url_kwargs` except
        url args are retrieved by default from state and if not
        available get kwargs from class attribute.

        :returns: dict of url_kwargs
        """
        kwargs = super(StatefulUrlParamsTestStep, self).get_url_kwargs()
        return self.state.get('url_kwargs', kwargs)
