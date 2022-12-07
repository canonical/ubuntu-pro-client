import mock

from lib.esm_cache import main


class TestUpdateEsmCaches:
    @mock.patch("lib.esm_cache.update_esm_caches")
    def test_builds_local_cache(self, m_update_caches, FakeConfig):
        main(FakeConfig())

        assert m_update_caches.call_count == 1
