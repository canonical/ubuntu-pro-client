from uaclient import exceptions, messages


class TestUbuntuProError:
    def test_uses_msg_when_subclass_defines_msg(self):
        class MsgOnlyError(exceptions.UbuntuProError):
            _msg = messages.NamedMessage("msg-only", "msg only path")

        exc = MsgOnlyError()

        assert exc.msg == "msg only path"
        assert exc.msg_code == "msg-only"
        assert str(exc) == "msg only path"
        assert exc.additional_info == {}

    def test_uses_formatted_msg_when_subclass_defines_formatted_msg(self):
        class FormattedOnlyError(exceptions.UbuntuProError):
            _formatted_msg = messages.FormattedNamedMessage(
                "formatted-only", "hello {name}"
            )

        exc = FormattedOnlyError(name="ubuntu")

        assert exc.msg == "hello ubuntu"
        assert exc.msg_code == "formatted-only"
        assert str(exc) == "hello ubuntu"
        assert exc.additional_info == {"name": "ubuntu"}
        assert getattr(exc, "name") == "ubuntu"

    def test_prefers_formatted_msg_when_both_are_defined(self):
        class BothDefinedError(exceptions.UbuntuProError):
            _msg = messages.NamedMessage("msg-branch", "from msg")
            _formatted_msg = messages.FormattedNamedMessage(
                "formatted-branch", "from formatted {value}"
            )

        exc = BothDefinedError(value="path")

        assert exc.msg == "from formatted path"
        assert exc.msg_code == "formatted-branch"

    def test_uses_safe_fallback_when_neither_is_defined(self):
        class NoMessageFieldsError(exceptions.UbuntuProError):
            pass

        exc = NoMessageFieldsError()

        assert exc.msg == "an unexpected error occurred."
        assert exc.msg_code == "ubuntu-pro-error"
        assert str(exc) == "an unexpected error occurred."


class TestAnonymousUbuntuProError:
    def test_from_named_msg(self):
        named_msg = messages.NamedMessage("test-code", "test message")

        exc = exceptions.AnonymousUbuntuProError(named_msg=named_msg)

        assert exc.named_msg == named_msg
        assert exc.msg == "test message"
        assert exc.msg_code == "test-code"
        assert str(exc) == "test message"
