"""
SubUI is a framework to ease the pain of writing and running
integration tests. The "SubUI" part means that it is not meant
to test any of the UI (like html validation) but instead
allows to make complete workflow server integration tests.

Introduction
------------

The framework consists of 3 main components:

1.  **SubUI test runner**

    This is the interface layer of the SubUI framework.
    In other words, test methods will instantiate the runner
    and use it to interact with the SubUI integration tests.
    Primary job of a SubUI test runner is to execute test
    steps (described below) in correct order and maintain
    state between steps if necessary.

    .. note:: Even though it is called test runner, it does not
       replace or even relate to ``nosetests`` test runner.

2.  **Test Steps**

    In the most part, this framework is meant to make integration
    tests for complete workflows (e.g. go to page 1 ->
    submit form and assert redirect to page 2 -> go to page 2).
    A test step is a self-contained piece of the complete workflow
    like "go to page 1". Combinations of multiple steps then make up
    the workflow. Since steps are independent, they should know how to
    complete their task (e.g. submit form via ``POST``) and validate
    that they got expected result from the server. To allow
    flexible validation, they themselves do not validate anything
    but use validators (described below) to inspect server response
    in very similar way to how Django Form Field uses validators to
    verify user-input.

3.  **Validator**

    Validator's task is to make assertions about the response from
    the server. All validators are pretty straight forwards like
    assert that the response status code is ``Redirect - 302``
    or that redirect header ``Location`` is returned. More complex
    assertions can be made by either using multiple validators
    in each test step or make more complex validator via
    multiple class inheritance.

Example
-------

An example should show some of the advantages of using this
framework for a hypothetical todo application:

.. code-block:: python
    :linenos:

    # define steps
    class GoToLogin(TestStep):
        url_name = 'login'
        request_method = 'get'
        validators = [StatusCodeOkValidator]

    class SubmitLoginForm(TestStep):
        url_name = 'form'
        validators = [RedirectToRouteValidator(expected_route_name='list')]
        data = {
            'username': 'user',
            'password': 'password',
        }

    class GoToList(TestStep):
        url_name = 'list'
        request_method = 'get'
        validators = [StatusCodeOkValidator]

    class CreateToDo(TestStep):
        url_name = 'create'
        validators = [RedirectToRouteValidator(expected_route_name='list')]
        data = {
            'notes': 'need to finish something',
            'due date': '2015-01-01',
        }

    # integration tests
    class TestWorkflow(TestCase):
        def test_login_and_create_todo(self):
            runner = SubUITestRunner(
                OrderedDict((
                    ('login', GoToLogin),
                    ('login_submit', SubmitLoginForm),
                    ('list1', GoToList),
                    ('create', CreateToDo),
                    ('list2', GoToList),
                )),
                client=self.client
            ).run()

            self.assertNotContains(runner.steps['list1'].response,
                                   'need to finish something')
            self.assertContains(runner.steps['list2'].response,
                                'need to finish something')

        def test_just_create(self):
            data = {
                'notes': 'other task here to complete',
                'due date': '2015-01-01',
            }
            runner = SubUITestRunner(
                OrderedDict((
                    ('list1', GoToList),
                    ('create', CreateToDo(data=data)),
                    ('list2', GoToList),
                )),
                client=self.client
            ).run()

            self.assertNotContains(runner.steps['list1'].response,
                                   'other task here to complete')
            self.assertContains(runner.steps['list2'].response,
                                'other task here to complete')

some useful things to note about what happened above:

* Reuse of test steps. Since each step is self-contained,
  they can be combined in different ways to make
  different integration tests. They can even be reused
  multiple times within the same integration test.
* Step attributes can easily be overwritten if need to like
  in ``test_just_create`` test method - ``CreateToDo``'s
  data is overwritten to post different values.
* Assertions on steps can be performed outside of the test
  runner. After steps are executed, all steps can be accessed
  via ``runner.steps`` attribute which will be an instance
  of :py:class:`collections.OrderedDict`.
* :py:class:`subui.validators.RedirectToRouteValidator`
  is combined validator via multiple inheritance which
  verifies that the response status code is 302 - Redirect;
  ``Location`` response header is present; and that
  the page redirects to a particular route as determined
  by Django's ``resolve``.

Advanced Use-Cases
------------------

More advanced things can be accomplished with the framework.
In the previous example, all steps had a fixed url without any
parameters. This example will use state to pass information
between steps:

.. code-block:: python
    :linenos:

    # login returns redirect to user profile with user id
    class LoginStep(TestStep):
        url_name = 'login'
        validators = [RedirectToRouteValidator(expected_route_name='profile')]
        data = {
            'username': 'username',
            'password': 'password',
        }

        def post_test_response(self):
            # extract user kwargs from redirect location
            resolved = resolve(self.response['Location'])
            self.state.push({
                'url_kwargs': resolved.kwargs,
            })

    class ProfileStep(StatefulUrlParamsTestStep):
        url_name = 'profile'  # requires url kwargs of username
        request_method = 'get'
        validators = [StatusCodeOkValidator]

    class EditProfileStep(StatefulUrlParamsTestStep):
        url_name = 'edit_profile'  # requires url kwarg of username
        validators = [StatusCodeOkValidator]

    class TestWorkflow(TestCase):
        def test_login_and_edit(self):
            data = {
                'username': 'otheruser',
                'password': 'otherpassword',
            }
            runner = SubUITestRunner(
                [
                    LoginStep,                   # 0
                    ProfileStep,                 # 1
                    EditProfileStep(data=data),  # 2
                    ProfileStep,                 # 3
                ],
                client=self.client
            ).run()

            self.assertContains(runner.steps[3].response,
                                'otheruser')

some notes about what happened:

* ``LoginStep`` uses a hook
  :py:meth:`subui.step.TestStep.post_test_response`
  to add data to a state. Since state is global for all steps within
  test runner, other steps can access it.
* ``ProfileStep`` and ``EditProfileStep`` subclass
  :py:class:`subui.step.StatefulUrlParamsTestStep`
  which uses state to get url args and kwargs.
* When using ``resolve`` in ``post_test_response``, there is no
  need to do ``try: except Resolver404`` since that will be executed
  after validator verifications hence it is guaranteed that
  the url will resolve without issues.
* Steps are provided as :py:func:`list` instead of
  :py:class:`collections.OrderedDict`. Test runner automatically converts
  the steps into :py:class:`collections.OrderedDict` with keys as indexes
  which allows to type test runner a bit faster ;-) in case you don't
  need to reference steps with particular keys.
"""
from __future__ import unicode_literals


__author__ = 'Miroslav Shubernetskiy'
__version__ = '0.2.1'
__description__ = 'Framework to make workflow server integration test suites'
