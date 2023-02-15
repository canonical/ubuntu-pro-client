import mock
import pytest

from uaclient.exceptions import UserFacingError
from uaclient.yaml import get_imported_yaml_module

M_PREFIX = "uaclient.yaml."


@mock.patch(M_PREFIX + "sys")
class TestYamlImport:
    def test_get_yaml_module_returns_imported(self, m_sys):
        imported_yaml = mock.MagicMock()
        m_sys.modules = {"yaml": imported_yaml}
        yaml = get_imported_yaml_module()
        assert yaml is imported_yaml

    @pytest.mark.parametrize("has_yaml_in_system", (True, False))
    @mock.patch(M_PREFIX + "importlib_machinery")
    @mock.patch(M_PREFIX + "importlib_util")
    def test_get_yaml_module_imports_from_system(
        self, m_util, m_machinery, m_sys, has_yaml_in_system
    ):
        m_sys.modules = {}

        m_yaml_spec = mock.MagicMock()
        m_yaml_module = mock.MagicMock()

        m_util.module_from_spec.return_value = m_yaml_module

        if has_yaml_in_system:
            m_machinery.PathFinder.find_spec.return_value = m_yaml_spec
        else:
            m_machinery.PathFinder.find_spec.return_value = None

        if has_yaml_in_system:
            yaml = get_imported_yaml_module()

            assert m_yaml_module == yaml
            assert [
                mock.call("yaml", path=["/usr/lib/python3/dist-packages"])
            ] == m_machinery.PathFinder.find_spec.call_args_list
            assert [
                mock.call(m_yaml_spec)
            ] == m_util.module_from_spec.call_args_list
            assert m_sys.modules["yaml"] == m_yaml_module
            assert [
                mock.call(m_yaml_module)
            ] == m_yaml_spec.loader.exec_module.call_args_list
        else:
            with pytest.raises(UserFacingError) as excinfo:
                yaml = get_imported_yaml_module()

            assert "missing-yaml-module" == excinfo.value.msg_code
            assert "Couldn't import the YAML module" in excinfo.value.msg
            assert [
                mock.call("yaml", path=["/usr/lib/python3/dist-packages"])
            ] == m_machinery.PathFinder.find_spec.call_args_list
