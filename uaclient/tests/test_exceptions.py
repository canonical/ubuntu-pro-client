from uaclient import exceptions, messages


class TestAnonymousUbuntuProError:
    def test_from_named_msg(self):
        named_msg = messages.NamedMessage("test-code", "test message")

        exc = exceptions.AnonymousUbuntuProError(named_msg=named_msg)

        assert exc.named_msg == named_msg
        assert exc.msg == "test message"
        assert exc.msg_code == "test-code"
        assert str(exc) == "test message"
