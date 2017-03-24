from __future__ import print_function, unicode_literals
import inspect
from collections import OrderedDict

from pycontext.context import Context


class SubUITestRunner(object):
    """
    SubUI Test Runner.

    This is the interface class of the SubUI framework.
    It runs all of the provided steps in the provided order.
    Since some steps might need state from previous executed
    steps, the runner maintains reference to a global state
    which it then passes to each step during execution.

    :var collections.OrderedDict steps: Test steps to be executed
    :var client: Django test client to run tests
    :var dict kwargs: Additional kwargs given to class.
        These kwargs will be provided to each step when executed.
    :var pycontext.context.Context state: State to be
        shared between test step executions.

    :param steps: Steps to be executed. Executed in the provided order
        hence need to be provided in order-maintaining data-structure.
    :type steps: list, tuple, collections.OrderedDict

    :param client: Django test Client to query server with
    :type client: django.test.client.Client

    :param state: State to be shared between step executions.
        Optional and by default is empty dict.
    :type state: dict

    :param kwargs: Additional kwargs to be passed to each
        step during initialization if it is not already provided
        as initialized object.
    """

    def __init__(self, steps, client, state=None, **kwargs):
        msg = 'SubUI steps can either be tuple, list or OrderedDict'
        assert isinstance(steps, (list, tuple, OrderedDict)), msg

        self.steps = steps
        self.client = client
        self.kwargs = kwargs

        self.state = Context(state or {})

        self._normalize_steps()

    def _normalize_steps(self):
        """
        Normalize steps - convert to :py:class:`collections.OrderedDict`
        and instantiate.

        This converts steps into :py:class:`collections.OrderedDict` if they are
        not already in which case the keys will be integer indexes of each step.
        Also this instantiates each step if is provided as a class.
        While instantiating it provides all the
        :py:attr:`SubUITestRunner.kwargs` given to runner.
        """
        if isinstance(self.steps, (list, tuple)):
            self.steps = OrderedDict(zip(range(len(self.steps)), self.steps))

        self.steps = OrderedDict(map(
            lambda s: (s[0], s[1](**self.kwargs)) if inspect.isclass(s[1]) else s,
            self.steps.items()
        ))

    def run(self):
        """
        Run the test runner.

        This executes all steps in the order there are defined
        in :py:attr:`SubUITestRunner.steps`. Before each step is executed
        :py:meth:`subui.step.TestStep.init`
        is called providing all the necessary attributes to execute
        the step like test client, steps, and state).

        :return: Reference to the test runner
        """
        for i, (key, step) in enumerate(self.steps.items()):
            step.init(client=self.client,
                      steps=self.steps,
                      step_index=i,
                      step_key=key,
                      state=self.state)
            step.request()
            step.test_response()

        return self
