from __future__ import print_function, unicode_literals
import inspect

from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import Resolver404, resolve
from django.template.response import SimpleTemplateResponse
from six.moves.urllib_parse import urlsplit, urlunsplit


class BaseValidator(object):
    """
    Base validator which should be sub-classed to create
    custom validators.

    :var tuple BaseValidator.expected_attrs: Required attributes for the
        validator. :py:meth:`_check_improper_configuration`
        will verify that all of these attributes are defined.

        .. note:: Each validator should only define required
            attributes for itself. :py:meth:`_get_expected_attrs`
            will automatically return required attributes
            from all current validator and base classes.

    :param test_step: :py:class:`subui.step.TestStep`
        instance which will be used to make assertions on.

        .. note:: This parameter is not really required in the
            ``__init__`` because the same step will be passed
            in :py:meth:`test` however is useful in ``__init__``
            in case subclass validator needs to apply custom
            login according to values from the ``step``.
    """
    expected_attrs = None

    def __init__(self, test_step=None, **kwargs):
        self.step = test_step
        self.__dict__.update(**kwargs)

    def _get_expected_attrs(self):
        """
        Get all required/expected attributes as defined by
        :py:attr:`expected_attrs` from all current and base
        classes.

        For example::

            class Validator1(BaseValidator):
                expected_attr = ('foo', 'bar')

            class Validator2(Validator1):
                expected_attr = ('hello', 'world')

            > validator = Validator2()
            > validator._get_expected_attrs()
            ['foo', 'bar', 'hello', 'world']

        :rtype: list
        """
        bases = inspect.getmro(self.__class__)
        attrs = set()
        for base in bases:
            attrs |= set(getattr(base, 'expected_attrs', None) or set())
        return list(sorted(attrs))

    def _check_improper_configuration(self):
        """
        Check that the validator is configured correctly
        by verifying that all attributes as returned by
        :py:meth:`_get_expected_attrs` are defined.

        :raises ImproperlyConfigured: If any of the required
            attributes are not defined.
        """
        for attr in self._get_expected_attrs():
            if not getattr(self, attr, None):
                msg = '{} requires to define {}'
                raise ImproperlyConfigured(
                    msg.format(self.__class__.__name__, attr)
                )

    def _get_base_error_message(self):
        """
        Get base error message which will be used in assertions
        """
        msg = 'Response for {{{key}:{step}}} requesting "{url}"'
        msg = msg.format(
            key=self.step.step_key,
            step=self.step.__class__.__name__,
            url=self.step.get_url(),
        )
        return msg

    def test(self, test_step):
        """
        Test the step's server response by making
        all the necessary assertions. This method
        by default saves the ``test_step`` parameter
        into :py:attr:`step` and validates the validator
        by using :py:meth:`_check_improper_configuration`.
        All subclass validators should actually implement
        assertions in this method.

        :param test_step: Test step
        """
        self.step = test_step
        self._check_improper_configuration()


class HeaderValidator(BaseValidator):
    """
    Validator which can check that a particular header
    is returned and that it is of particular value.

    :var str HeaderValidator.header_name: Name of the header which
        must be returned
    :var str expected_header: Expected header value
        to be returned
    :var bool HeaderValidator.test_header_value: Whether to test the
        header value or simply check its existence
    :var test_contains_value: Whether to test if the
        header value contains another value, or simply
        check equality to that value
    """
    expected_attrs = ('header_name', 'expected_header',)
    header_name = None
    expected_header = None
    test_header_value = True
    test_contains_value = False

    def _get_expected_attrs(self):
        """
        Get all expected attributes except remove "expected_header"
        if :py:attr:`test_header_value` is ``False``.
        """
        attrs = super(HeaderValidator, self)._get_expected_attrs()

        if not self.test_header_value:
            attrs.remove('expected_header')

        return attrs

    def test(self, test_step):
        """
        Test the response returned with
        :py:attr:header_name header and that its value
        is equal to :py:attr:expected_header if
        :py:attr:test_header_value is True.
        If :py:attr:test_contains_value is True,
        header value will be tested to contain expected value.
        """
        super(HeaderValidator, self).test(test_step)
        if self.test_contains_value:
            self.test_header_value = False
        self.step.test.assertIn(
            self.header_name,
            self.step.response,
            '{} must contain {} header'
            ''.format(self._get_base_error_message(),
                      self.header_name)
        )
        if self.test_header_value:
            self.test_contains_value = False
            self.step.test.assertEqual(
                self.step.response[self.header_name],
                self.expected_header,
                '{} returned header {} with value {} != {}'
                ''.format(self._get_base_error_message(),
                          self.header_name,
                          self.step.response[self.header_name],
                          self.expected_header)
            )
        if self.test_contains_value:
            self.step.test.assertIn(
                self.expected_header,
                self.step.response[self.header_name],
                '{} returned header {} with value {} which doesnt contain {}'
                ''.format(self._get_base_error_message(),
                          self.header_name,
                          self.step.response[self.header_name],
                          self.expected_header)
            )


class HeaderContentTypeValidator(HeaderValidator):
    """
    Validator to check that the expected
    "Content-Type" header is returned.
    """
    header_name = 'Content-Type'


class HeaderLocationValidator(HeaderValidator):
    """
    Validator to check that the redirect
    "Location" header is returned
    """
    header_name = 'Location'


class StatusCodeValidator(BaseValidator):
    """
    Validator which allows to verify the returned
    server status code such as "OK-200" or "Redirect-302", etc.

    :var int StatusCodeValidator.expected_status_code: Expected status code to be
        returned by the server
    """
    expected_attrs = ('expected_status_code',)
    expected_status_code = None

    def test(self, test_step):
        """
        Test that the response status code
        matched expected status code.
        """
        super(StatusCodeValidator, self).test(test_step)

        self.step.test.assertEqual(
            self.step.response.status_code,
            self.expected_status_code,
            '{} returned with status code {} != {}'
            ''.format(self._get_base_error_message(),
                      self.step.response.status_code,
                      self.expected_status_code)
        )


class StatusCodeOkValidator(StatusCodeValidator):
    """
    Validator to check that the returned status
    code is OK - 200
    """
    expected_status_code = 200


class StatusCodeRedirectValidator(HeaderLocationValidator, StatusCodeValidator):
    """
    Validator to check that the server returns a redirect
    with the "Location" header defined.
    """
    expected_status_code = 302
    test_header_value = False


class RedirectToRouteValidator(StatusCodeRedirectValidator):
    """
    Validator which also checks that the server returns
    a redirect to an expected Django route.

    :var str expected_route_name: Route name to which
        the server should redirect to
    """
    expected_attrs = ('expected_route_name',)
    expected_route_name = None

    def test(self, test_step):
        """
        Test the response by additionally testing
        that the response redirects to an expected
        route as defined by :py:attr:`expected_route_name`.
        """
        super(RedirectToRouteValidator, self).test(test_step)

        location = self.step.response['Location']
        # remove schema, query string and host from URL. Since query string need to be removed to properly resolve that url
        location = urlunsplit(('', '', urlsplit(location).path, '', ''))

        try:
            redirected_to_route = resolve(location).view_name
        except Resolver404:
            msg = '{} returned a redirect to "{}" which cannot be resolved'
            self.step.test.fail(msg.format(self._get_base_error_message(),
                                           location))

        self.step.test.assertEqual(
            redirected_to_route,
            self.expected_route_name,
            '{} returned redirect to route {} != {}'
            ''.format(self._get_base_error_message(),
                      redirected_to_route,
                      self.expected_route_name)
        )


class ResponseContentContainsValidator(StatusCodeOkValidator):
    """
    Validator which also checks that returned response
    content contains expect string.

    :var str expected_content: Expected string in the
        server response
    """
    expected_attrs = ('expected_content',)
    expected_content = None

    def test(self, test_step):
        """
        Test the response by additionally testing
        that the response context contains expected
        string as defined by :py:attr:`expected_content`.
        """
        super(ResponseContentContainsValidator, self).test(test_step)

        self.step.test.assertIn(
            self.expected_content,
            # need to decode since content is binary
            self.step.response.content.decode('utf-8'),
            '{} does not contain {!r} in its content'
            ''.format(self._get_base_error_message(),
                      self.expected_content)
        )


class ResponseContentNotContainsValidator(StatusCodeOkValidator):
    """
    Validator checks that returned response
    content does not contain unexpected string.

    :var str unexpected_content: Unexpected string in the
        server response
    """
    expected_attrs = ('unexpected_content',)
    unexpected_content = None

    def test(self, test_step):
        """
        Test the response by additionally testing
        that the response context does not contain the unexpected
        string as defined by :py:attr:`unexpected_content`.
        """
        super(ResponseContentNotContainsValidator, self).test(test_step)

        self.step.test.assertNotIn(
            self.unexpected_content,
            # need to decode since content is binary
            self.step.response.content.decode('utf-8'),
            'UnexpectedContentFound: {} contains {!r} in its content. '
            ''.format(self._get_base_error_message(),
                      self.unexpected_content)
        )


class SessionDataValidator(BaseValidator):
    """
    Validator which allows to verify the data in the session based on
    session key.

    :var str expected_session_key: Expected session key to be present in session
    :var list expected_session_secondary_keys: List of Expected session key to be present in session
    """
    expected_attrs = ('expected_session_key',)
    expected_session_key = None
    expected_session_secondary_keys = []

    def test(self, test_step):
        """
        Test that expected session key is present. If expected session data provided,
        ensure the expected session key data matches what is there currently.
        """
        super(SessionDataValidator, self).test(test_step)
        self.step.test.assertIn(
            self.expected_session_key,
            self.step.response.wsgi_request.session.keys(),
            '{} does not contain session[{!r}].'
            ''.format(self._get_base_error_message(),
                      self.expected_session_key)
        )
        if self.expected_session_secondary_keys:
            self.step.test.assertIsInstance(
                self.step.response.wsgi_request.session[self.expected_session_key],
                dict,
                '{} session[{!r}] is not a dictionary hence cannot contain secondary keys.'
                ''.format(self._get_base_error_message(), self.expected_session_key)
            )
        # Make sure secondary keys are not empty.
        for secondary_key in self.expected_session_secondary_keys:
            self.step.test.assertIn(
                secondary_key,
                self.step.response.wsgi_request.session[self.expected_session_key].keys(),
                '{} does not contain session[{!r}][{!r}].'
                ''.format(self._get_base_error_message(), self.expected_session_key, secondary_key)
            )
            self.step.test.assertIsNotNone(
                self.step.response.wsgi_request.session[self.expected_session_key][secondary_key],
                '{} contains session[{!r}][{!r}] but is empty.'
                ''.format(self._get_base_error_message(), self.expected_session_key, secondary_key)
            )


class FormInitialDataValidator(BaseValidator):
    """
    Validator checks that form in response has expected data in initial data.

    :var str initial_data_key: Expected initial data key to be present in form initial data
    :var expected_initial_data_value: Expected value initial value should be set to
    :var str context_data_form_name: Template context data key for form data
    :var bool test_initial_value: Test if the initial value matched expected value
    :var bool test_initial_value_present: Test if the initial value key is present in initial data
    :var bool test_initial_value_not_none: Test if the initial value is not ``None``
    """
    expected_attrs = ('initial_data_key',)
    initial_data_key = None
    expected_initial_data_value = None
    context_data_form_name = 'form'

    test_initial_value = False
    test_initial_value_present = True
    test_initial_value_not_none = True

    def test(self, test_step):
        super(FormInitialDataValidator, self).test(test_step)

        self.step.test.assertIsInstance(
            self.step.response,
            SimpleTemplateResponse,
            '{} did not return SimpleTemplateResponse '
            'and as such response.context_data is not accessible. '
            'It returned {!r}'
            ''.format(self._get_base_error_message(),
                      type(self.step.response))
        )

        self.step.test.assertIn(
            self.context_data_form_name,
            self.step.response.context_data,
            '{} did not render with {!r} in its context_data'
            ''.format(self._get_base_error_message(),
                      self.context_data_form_name)
        )

        self.step.test.assertIsInstance(
            self.step.response.context_data[self.context_data_form_name].initial,
            dict,
            '{} did not render with the context_data[{!r}].initial being a dictionary'
            ''.format(self._get_base_error_message(),
                      self.context_data_form_name)
        )

        if self.test_initial_value_present:
            self.step.test.assertIn(
                self.initial_data_key,
                self.step.response.context_data[self.context_data_form_name].initial.keys(),
                '{} did not render with {!r} in the context_data[{!r}].initial. '
                'Provided keys - {!r}'
                ''.format(self._get_base_error_message(),
                          self.initial_data_key,
                          self.context_data_form_name,
                          self.step.response.context_data[self.context_data_form_name].initial.keys())
            )

        if self.test_initial_value_not_none:
            self.step.test.assertIsNotNone(
                self.step.response.context_data['form'].initial[self.initial_data_key],
                '{} rendered with {!r} for context_data[{!r}].initial[{!r}]'
                ''.format(self._get_base_error_message(),
                          None,
                          self.context_data_form_name,
                          self.initial_data_key)
            )

        if self.test_initial_value:
            self.step.test.assertEqual(
                self.step.response.context_data['form'].initial[self.initial_data_key],
                self.expected_initial_data_value,
                '{} rendered with context_data[{!r}].initial[{!r}] = {} != {}'
                ''.format(self._get_base_error_message(),
                          self.context_data_form_name,
                          self.initial_data_key,
                          self.step.response.context_data['form'].initial[self.initial_data_key],
                          self.expected_initial_data_value)
            )
