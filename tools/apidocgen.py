"""
Generate RST documentation for an ubuntu-pro-client api endpoint.

For a single endpoint: python3 tools/apidocgen.py $ENDPOINT_NAME
For complete API reference documentation: python3 tools/apidocgen.py
"""

import sys
import textwrap
from importlib import import_module

sys.path.insert(0, ".")

from uaclient import data_types  # noqa: E402
from uaclient.api.api import VALID_ENDPOINTS  # noqa: E402
from uaclient.exceptions import UbuntuProError  # noqa: E402

BLOCK_INDENT = "   "
LIST_INDENT = "  "
NO_ARGS = "- This endpoint takes no arguments."
NO_FIELDS = "- This object has no fields."

ENDPOINT_TEMPLATE = """\
{name}
{underline}

{description}

- Introduced in Ubuntu Pro Client Version: ``{introduced_in}~``
- Requires network access: {requires_network}

Arguments:

{args_section}

.. tab-set::

   .. tab-item:: Python API interaction
      :sync: python

      **Calling from Python code:**

      .. code-block:: python

         {example_python}

      **Expected return object:**

      {result_classes}

      **Raised exceptions:**

      {exceptions}

   .. tab-item:: CLI interaction
      :sync: CLI

      **Calling from the CLI:**

      .. code-block:: bash

         {example_cli}

      {example_cli_extra}

      **Expected attributes in JSON structure:**

      .. code-block:: js

         {example_json}

{extra}

"""


def data_value_type_to_str(data_value_cls):
    if data_value_cls.__name__ == "_DataList":
        return "List[{}]".format(
            data_value_type_to_str(data_value_cls.item_cls)
        )
    if issubclass(data_value_cls, data_types.DataObject):
        return data_value_cls.__name__
    return data_value_cls.python_type_name


def create_fields_table(cls):
    table_template = """
.. list-table::
   :header-rows: 1

   * - Field Name
     - Type
     - Description
{fields}"""
    field_definition_template = """
* - ``{name}``
  - ``{type}``
  - {description}"""

    if len(cls.fields) == 0:
        return NO_FIELDS

    fields = []
    for field in cls.fields:
        type_str = data_value_type_to_str(field.data_cls)
        if not field.required:
            type_str = "Optional[{}]".format(type_str)
        fields.append(
            textwrap.indent(
                field_definition_template.format(
                    name=field.key, type=type_str, description=field.doc or ""
                ).strip(),
                prefix=BLOCK_INDENT,
            )
        )
    return table_template.format(
        fields="\n".join(fields),
    ).strip()


def collect_data_object_classes(target_cls, collection, *, ignore=[]):
    for field in target_cls.fields:
        cls = field.data_cls
        if cls.__name__ == "_DataList":
            cls = cls.item_cls
        if (
            issubclass(cls, data_types.DataObject)
            and cls not in collection
            and cls not in ignore
        ):
            collection.append(cls)
            collect_data_object_classes(cls, collection, ignore=[])


def print_endpoint_docs(endpoint_name):
    module = import_module("uaclient.api." + endpoint_name)

    if module.endpoint.options_cls is None:
        args_section = NO_ARGS
    else:
        args_section = create_fields_table(module.endpoint.options_cls)
    extra_args_content = module._doc.get("extra_args_content")
    if extra_args_content:
        args_section += "\n\n" + extra_args_content.strip()

    result_class = module._doc.get("result_class")
    result_classes = [result_class]
    collect_data_object_classes(
        result_class,
        result_classes,
        ignore=module._doc.get("ignore_result_classes", []),
    )
    result_classes += module._doc.get("extra_result_classes", [])
    class_definition_template = """
- ``{module}.{name}``

{fields_table}
    """
    result_class_definitions = []
    for cls in result_classes:
        result_class_definitions.append(
            class_definition_template.format(
                module=cls.__module__,
                name=cls.__qualname__,
                fields_table=textwrap.indent(
                    create_fields_table(cls), LIST_INDENT
                ),
            ).strip()
        )
    result_class_definitions_str = textwrap.indent(
        "\n\n".join(result_class_definitions),
        prefix=BLOCK_INDENT * 2,
    ).strip()

    possible_exceptions = [
        (
            UbuntuProError,
            (
                "``UbuntuProError`` is the base class of all exceptions raised"
                " by Ubuntu Pro Client and it is best practice to handle this"
                " error on any API call. (Note: if any API call raises an"
                " exception that does not inherit from ``UbuntuProError``,"
                " please report a bug)."
            ),
        )
    ] + module._doc.get("exceptions", [])
    exception_str_list = []
    for err_cls, msg in possible_exceptions:
        exception_str_list.append(
            "- ``{name}``: {msg}".format(name=err_cls.__name__, msg=msg)
        )
    exceptions_str = textwrap.indent(
        "\n".join(exception_str_list), prefix=BLOCK_INDENT * 2
    ).strip()

    extra_indent = module._doc.get("extra_indent", 1)

    data = {
        "name": endpoint_name,
        "underline": "=" * len(endpoint_name),
        "description": textwrap.dedent(module.endpoint.fn.__doc__).strip(),
        "introduced_in": module._doc.get("introduced_in"),
        "requires_network": "Yes" if module._doc["requires_network"] else "No",
        "args_section": args_section,
        "example_python": textwrap.indent(
            module._doc.get("example_python").strip(),
            prefix=BLOCK_INDENT * 3,
        ).strip(),
        "result_classes": result_class_definitions_str,
        "exceptions": exceptions_str,
        "example_cli": module._doc.get("example_cli").strip(),
        "example_cli_extra": textwrap.indent(
            module._doc.get("example_cli_extra", ""),
            prefix=BLOCK_INDENT * 2,
        ).strip(),
        "example_json": textwrap.indent(
            module._doc.get("example_json").strip(),
            prefix=BLOCK_INDENT * 3,
        ).strip(),
        "extra": textwrap.indent(
            module._doc.get("extra", "").strip(),
            prefix=BLOCK_INDENT * extra_indent,
        ),
    }

    print(ENDPOINT_TEMPLATE.format(**data))


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # assume arg is endpoint name
        endpoint_name = sys.argv[1]
        try:
            print_endpoint_docs(endpoint_name)
        except ModuleNotFoundError:
            print(f"Endpoint `{endpoint_name}` does not exist")
            sys.exit(1)
    else:
        # all
        print(
            """\
..
   THIS DOCUMENTATION WAS AUTOMATICALLY GENERATED
   Do not edit this document directly. Instead, edit the metadata in the api
   source code. The api source code can be found on the main branch of the git
   repo at https://github.com/canonical/ubuntu-pro-client. The api source code
   is nested in the uaclient/api folder. If you need to edit the documentation
   for u.pro.version.v1 you can find the api source code in
   uaclient/api/u/pro/version/v1.py The documentation metadata is at the bottom
   of that file.
"""
        )
        print()
        print("Available endpoints")
        print("===================")
        print()
        print("The currently available endpoints are:")
        print()
        for e in VALID_ENDPOINTS:
            print(f"- `{e}`_")
        print()
        for e in VALID_ENDPOINTS:
            try:
                print_endpoint_docs(e)
            except Exception:
                msg = f"Failed generating docs for {e}"
                print(msg)
                print("^" * len(msg))
                raise
