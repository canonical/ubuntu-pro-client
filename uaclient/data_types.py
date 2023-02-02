import datetime
import json
from enum import Enum
from typing import Any, List, Optional, Type, TypeVar, Union

from uaclient import exceptions, messages, util


class IncorrectTypeError(exceptions.UserFacingError):
    def __init__(self, expected_type: str, got_type: str):
        msg = messages.INCORRECT_TYPE_ERROR_MESSAGE.format(
            expected_type=expected_type, got_type=got_type
        )
        super().__init__(msg.msg, msg.name)
        self.expected_type = expected_type
        self.got_type = got_type


class IncorrectListElementTypeError(IncorrectTypeError):
    def __init__(self, err: IncorrectTypeError, at_index: int):
        msg = messages.INCORRECT_LIST_ELEMENT_TYPE_ERROR_MESSAGE.format(
            index=at_index, nested_msg=err.msg
        )
        self.msg = msg.msg
        self.msg_code = msg.name
        self.additional_info = None
        self.expected_type = err.expected_type
        self.got_type = err.got_type


class IncorrectFieldTypeError(IncorrectTypeError):
    def __init__(self, err: IncorrectTypeError, key: str):
        msg = messages.INCORRECT_FIELD_TYPE_ERROR_MESSAGE.format(
            key=key, nested_msg=err.msg
        )
        self.msg = msg.msg
        self.msg_code = msg.name
        self.additional_info = None
        self.key = key
        self.expected_type = err.expected_type
        self.got_type = err.got_type


class IncorrectEnumValueError(IncorrectTypeError):
    def __init__(self, values: List[Union[str, int]], enum_class: Any):
        msg = messages.INCORRECT_ENUM_VALUE_ERROR_MESSAGE.format(
            values=values, enum_class=repr(enum_class)
        )
        self.msg = msg.msg
        self.msg_code = msg.name
        self.additional_info = None
        self.expected_type = "one of: {}".format(
            ", ".join([str(v) for v in values])
        )
        self.got_type = "<invalid_value>"


class DataValue:
    """
    Generic data value to be extended by more specific typed data values.
    This establishes the interface of a static/class method called `from_value`
    that returns the parsed value if appropriate.
    """

    @staticmethod
    def from_value(val: Any) -> Any:
        return val


E = TypeVar("E", bound="EnumDataValue")


class EnumDataValue(DataValue, Enum):
    """
    To be used for parsing enum values
    from_value raises an error if the value is not in the enum class values
    and returns the value if found.
    """

    @classmethod
    def from_value(cls: Type[E], val: Any) -> E:
        try:
            return cls(val)
        except ValueError:
            values = [i.value for i in cls]
            raise IncorrectEnumValueError(values, cls)


class StringDataValue(DataValue):
    """
    To be used for parsing string values
    from_value raises an error if the value is not a string and returns
    the string itself if it is a string.
    """

    @staticmethod
    def from_value(val: Any) -> str:
        if not isinstance(val, str):
            raise IncorrectTypeError("str", type(val).__name__)
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
            raise IncorrectTypeError("int", type(val).__name__)
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
            raise IncorrectTypeError("bool", type(val).__name__)
        return val


class DatetimeDataValue(DataValue):
    """
    This expects that value is a datetime.
    from_value raises an error if the value is not a datetime and returns
    the datetime itself if it is a datetime.
    """

    @staticmethod
    def from_value(val: Any) -> datetime.datetime:
        if not isinstance(val, datetime.datetime):
            raise IncorrectTypeError("datetime", type(val).__name__)
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
                raise IncorrectTypeError("list", type(val).__name__)
            new_val = []
            for i, item in enumerate(val):
                try:
                    new_val.append(data_cls.from_value(item))
                except IncorrectTypeError as e:
                    raise IncorrectListElementTypeError(e, i)
            return new_val

    return _DataList


def data_list_to_list(
    val: List[Union["DataObject", list, str, int, bool, Enum]],
    keep_none: bool = True,
) -> list:
    new_val = []  # type: list
    for item in val:
        if isinstance(item, DataObject):
            new_val.append(item.to_dict(keep_none))
        elif isinstance(item, list):
            new_val.append(data_list_to_list(item, keep_none))
        elif isinstance(item, Enum):
            new_val.append(item.value)
        else:
            new_val.append(item)
    return new_val


class Field:
    """
    For defining the fields static property of a DataObject.
    """

    def __init__(
        self,
        key: str,
        data_cls: Type[DataValue],
        required: bool = True,
        dict_key: Optional[str] = None,
    ):
        self.key = key
        self.data_cls = data_cls
        self.required = required
        if dict_key is not None:
            self.dict_key = dict_key
        else:
            self.dict_key = self.key


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

    def __eq__(self, other):
        for field in self.fields:
            self_val = getattr(self, field.key, None)
            other_val = getattr(other, field.key, None)
            if self_val != other_val:
                return False
        return True

    def __repr__(self):
        return "{}{}".format(
            self.__class__.__name__, self.to_dict().__repr__()
        )

    def to_dict(self, keep_none: bool = True) -> dict:
        d = {}
        for field in self.fields:
            val = getattr(self, field.key, None)
            new_val = None  # type: Any

            if isinstance(val, DataObject):
                new_val = val.to_dict(keep_none)
            elif isinstance(val, list):
                new_val = data_list_to_list(val, keep_none)
            elif isinstance(val, Enum):
                new_val = val.value
            else:
                # simple type, just copy
                new_val = val

            if new_val is not None or keep_none:
                d[field.dict_key] = new_val
        return d

    def to_json(self, keep_null: bool = True) -> str:
        return json.dumps(
            self.to_dict(keep_none=keep_null),
            sort_keys=True,
            cls=util.DatetimeAwareJSONEncoder,
        )

    @classmethod
    def from_dict(
        cls: Type[T], d: dict, optional_type_errors_become_null: bool = False
    ) -> T:
        kwargs = {}
        for field in cls.fields:
            try:
                val = d[field.dict_key]
            except KeyError:
                if field.required:
                    raise IncorrectFieldTypeError(
                        IncorrectTypeError(field.data_cls.__name__, "null"),
                        field.dict_key,
                    )
                else:
                    val = None
            if val is not None:
                try:
                    val = field.data_cls.from_value(val)
                except IncorrectTypeError as e:
                    if not field.required and optional_type_errors_become_null:
                        # SC-1428: we should warn here, but this currently runs
                        # before setup_logging() in the case of
                        # user-config.json.
                        #
                        # logging.warning(
                        #     "{} is wrong type (expected {} but got {}) but "
                        #     "considered optional - treating as null".format(
                        #         field.key, e.expected_type, e.got_type
                        #     )
                        # )
                        val = None
                    else:
                        raise IncorrectFieldTypeError(e, field.dict_key)

            kwargs[field.key] = val
        return cls(**kwargs)

    @classmethod
    def from_value(cls, val: Any):
        if not isinstance(val, dict):
            raise IncorrectTypeError("dict", type(val).__name__)
        return cls.from_dict(val)


class AttachActionsConfigFile(DataObject):
    """
    The format of the yaml file that can be passed with
    pro attach --attach-config /path/to/file
    """

    fields = [
        Field("token", StringDataValue),
        Field("enable_services", data_list(StringDataValue), required=False),
    ]

    def __init__(self, *, token: str, enable_services: Optional[List[str]]):
        self.token = token
        self.enable_services = enable_services
