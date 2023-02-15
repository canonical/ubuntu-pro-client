import sys
from importlib import machinery as importlib_machinery
from importlib import util as importlib_util

from uaclient.exceptions import UserFacingError
from uaclient.messages import MISSING_YAML_MODULE


def get_imported_yaml_module():
    # Maybe we already imported it?
    if "yaml" in sys.modules:
        return sys.modules["yaml"]

    # Try to get the system yaml module
    pyyaml_spec = importlib_machinery.PathFinder.find_spec(
        "yaml", path=["/usr/lib/python3/dist-packages"]
    )
    # If there is no system 'yaml' module (which is weird enough),
    # then raise an exception asking for it to be there
    if pyyaml_spec is None:
        raise UserFacingError(
            MISSING_YAML_MODULE.msg, MISSING_YAML_MODULE.name
        )

    # Import it!
    yaml_module = importlib_util.module_from_spec(pyyaml_spec)
    sys.modules["yaml"] = yaml_module
    loader = pyyaml_spec.loader
    # The loader shouldn't be None, documentation says:
    # "The finder should always set this attribute."
    # But mypy complains, so we check anyway.
    if loader is not None:
        loader.exec_module(yaml_module)

    return yaml_module


yaml = get_imported_yaml_module()

safe_load = yaml.safe_load
safe_dump = yaml.safe_dump
parser = yaml.parser
