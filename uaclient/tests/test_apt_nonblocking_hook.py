import mock

from lib.apt_update_nonblocking_hook import main


class TestAptNonBlockingHook:
    @mock.patch("lib.apt_update_nonblocking_hook.update_esm_caches")
    def test_builds_local_cache(self, m_update_caches, FakeConfig):
        main(FakeConfig())

        assert m_update_caches.call_count == 1
