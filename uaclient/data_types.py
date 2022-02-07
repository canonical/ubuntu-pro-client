from typing import Any, List, Optional, Type, TypeVar

from uaclient import exceptions

INCORRECT_TYPE_ERROR_MESSAGE = (
    "Expected value with type {type} but got value: {value}"
)
INCORRECT_LIST_ELEMENT_TYPE_ERROR_MESSAGE = (
    "Got value with incorrect type at index {index}: {nested_msg}"
)
INCORRECT_FIELD_TYPE_ERROR_MESSAGE = (
    'Got value with incorrect type for field "{key}": {nested_msg}'
)


class IncorrectTypeError(exceptions.UserFacingError):
    def __init__(self, expected_type: str, got_value: Any):
        super().__init__(
            INCORRECT_TYPE_ERROR_MESSAGE.format(
                type=expected_type, value=repr(got_value)
            )
        )


class IncorrectListElementTypeError(IncorrectTypeError):
    def __init__(self, err: IncorrectTypeError, at_index: int):
        self.msg = INCORRECT_LIST_ELEMENT_TYPE_ERROR_MESSAGE.format(
            index=at_index, nested_msg=err.msg
        )


class IncorrectFieldTypeError(IncorrectTypeError):
    def __init__(self, err: IncorrectTypeError, key: str):
        self.msg = INCORRECT_FIELD_TYPE_ERROR_MESSAGE.format(
            key=key, nested_msg=err.msg
        )


class DataValue:
    """
    Generic data value to be extended by more specific typed data values.
    This establishes the interface of a static/class method called `from_value`
    that returns the parsed value if appropriate.
    """

    @staticmethod
    def from_value(val: Any) -> Any:
        return val


class StringDataValue(DataValue):
    """
    To be used for parsing string values
    from_value raises an error if the value is not a string and returns
    the string itself if it is a string.
    """

    @staticmethod
    def from_value(val: Any) -> str:
        if not isinstance(val, str):
            raise IncorrectTypeError("string", val)
        return val


class IntDataValue(DataValue):
    """
    To be used for parsing int values
    from_value raises an error if the value is not a int and returns
    the int itself if it is a int.
    """

    @staticmethod
    def from_value(val: Any) -> int:
        if not isinstance(val, int) or isinstance(val, bool):
            raise IncorrectTypeError("int", val)
        return val


class BoolDataValue(DataValue):
    """
    To be used for parsing bool values
    from_value raises an error if the value is not a bool and returns
    the bool itself if it is a bool.
    """

    @staticmethod
    def from_value(val: Any) -> bool:
        if not isinstance(val, bool):
            raise IncorrectTypeError("bool", val)
        return val


def data_list(data_cls: Type[DataValue]) -> Type[DataValue]:
    """
    To be used for parsing lists of a certain DataValue type.
    Returns a class that extends DataValue and validates that
    each item in a list is the correct type in its from_value.
    """

    class _DataList(DataValue):
        @staticmethod
        def from_value(val: Any) -> List:
            if not isinstance(val, list):
                raise IncorrectTypeError("list", val)
            for i, item in enumerate(val):
                try:
                    val[i] = data_cls.from_value(item)
                except IncorrectTypeError as e:
                    raise IncorrectListElementTypeError(e, i)
            return val

    return _DataList


class Field:
    """
    For defining the fields static property of a DataObject.
    """

    def __init__(
        self, key: str, data_cls: Type[DataValue], required: bool = True
    ):
        self.key = key
        self.data_cls = data_cls
        self.required = required


T = TypeVar("T", bound="DataObject")


class DataObject(DataValue):
    """
    For defining a python object that can be parsed from a dict.
    Validates that a set of expected fields are present in the dict
    that is parsed and that the values of those fields are the correct
    DataValue by calling from_value on each.
    The fields are defined using the `fields` static property.
    DataObjects can be used in Fields of other DataObjects.
    To define a new DataObject:
      1. Create a new class that extends DataObject.
      2. Define the `fields` static property to be a list of Field objects
      3. Define the constructor to take kwargs that match the list of Field
         objects.
           a. Example 1: Field("keyname", StringDataValue) -> keyname: str
           b. Example 2: Field("keyname", data_list(IntDataValue), required=False) -> keyname: Optional[List[int]]  # noqa: E501
      4. Use from_value or from_dict to parse a dict into the python object.
    """

    fields = []  # type: List[Field]

    def __init__(self, **_kwargs):
        pass

    @classmethod
    def from_dict(cls: Type[T], d: dict) -> T:
        kwargs = {}
        for field in cls.fields:
            try:
                val = d[field.key]
            except KeyError:
                if field.required:
                    raise IncorrectFieldTypeError(
                        IncorrectTypeError(field.data_cls.__name__, None),
                        field.key,
                    )
                else:
                    val = None
            if val is not None:
                try:
                    val = field.data_cls.from_value(val)
                except IncorrectTypeError as e:
                    raise IncorrectFieldTypeError(e, field.key)
            kwargs[field.key] = val
        return cls(**kwargs)

    @classmethod
    def from_value(cls, val: Any):
        if not isinstance(val, dict):
            raise IncorrectTypeError("dict", val)
        return cls.from_dict(val)


class AttachActionsConfigFile(DataObject):
    """
    The format of the yaml file that can be passed with
    ua attach --attach-config /path/to/file
    """

    fields = [
        Field("token", StringDataValue),
        Field("enable_services", data_list(StringDataValue), required=False),
    ]

    def __init__(self, *, token: str, enable_services: Optional[List[str]]):
        self.token = token
        self.enable_services = enable_services
