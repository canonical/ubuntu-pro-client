from typing import List, Optional

import pytest

from uaclient.data_types import (
    BoolDataValue,
    DataObject,
    DataValue,
    Field,
    IncorrectFieldTypeError,
    IncorrectListElementTypeError,
    IncorrectTypeError,
    IntDataValue,
    StringDataValue,
    data_list,
)

M_PATH = "uaclient.data_types"


class TestDataValues:
    @pytest.mark.parametrize(
        "val", (1, "hello", {"key": "value"}, ["one", "two"])
    )
    def test_data_value(self, val):
        assert val == DataValue.from_value(val)

    @pytest.mark.parametrize("val", ("hello", "key", "one", "two"))
    def test_string_data_value_success(self, val):
        result = StringDataValue.from_value(val)
        assert val == result
        assert isinstance(result, str)

    @pytest.mark.parametrize(
        "val, error",
        (
            (True, IncorrectTypeError("string", True)),
            (1, IncorrectTypeError("string", 1)),
            ([], IncorrectTypeError("string", [])),
            ({}, IncorrectTypeError("string", {})),
        ),
    )
    def test_string_data_value_error(self, val, error):
        with pytest.raises(type(error)) as e:
            StringDataValue.from_value(val)
        assert e.value.msg == error.msg

    @pytest.mark.parametrize("val", (1, 0, -1))
    def test_int_data_value_success(self, val):
        result = IntDataValue.from_value(val)
        assert val == result
        assert isinstance(result, int)

    @pytest.mark.parametrize(
        "val, error",
        (
            (True, IncorrectTypeError("int", True)),
            ("hello", IncorrectTypeError("int", "hello")),
            ("1", IncorrectTypeError("int", "1")),
            ([], IncorrectTypeError("int", [])),
            ({}, IncorrectTypeError("int", {})),
        ),
    )
    def test_int_data_value_error(self, val, error):
        with pytest.raises(type(error)) as e:
            IntDataValue.from_value(val)
        assert e.value.msg == error.msg

    @pytest.mark.parametrize("val", (True, False))
    def test_bool_data_value_success(self, val):
        result = BoolDataValue.from_value(val)
        assert val == result
        assert isinstance(result, bool)

    @pytest.mark.parametrize(
        "val, error",
        (
            ("hello", IncorrectTypeError("bool", "hello")),
            (1, IncorrectTypeError("bool", 1)),
            ([], IncorrectTypeError("bool", [])),
            ({}, IncorrectTypeError("bool", {})),
        ),
    )
    def test_bool_data_value_error(self, val, error):
        with pytest.raises(type(error)) as e:
            BoolDataValue.from_value(val)
        assert e.value.msg == error.msg


class TestDataList:
    @pytest.mark.parametrize(
        "data_cls, val",
        (
            (IntDataValue, []),
            (IntDataValue, [0]),
            (IntDataValue, [0, 4, -3, 2, 1]),
            (StringDataValue, []),
            (StringDataValue, ["hello"]),
            (StringDataValue, ["one", "two", "three"]),
        ),
    )
    def test_success(self, data_cls, val):
        result = data_list(data_cls).from_value(val)
        assert val == result

    @pytest.mark.parametrize(
        "data_cls, val, error",
        (
            (IntDataValue, "hello", IncorrectTypeError("list", "hello")),
            (IntDataValue, 1, IncorrectTypeError("list", 1)),
            (IntDataValue, {}, IncorrectTypeError("list", {})),
            (
                IntDataValue,
                ["one"],
                IncorrectListElementTypeError(
                    IncorrectTypeError("int", "one"), 0
                ),
            ),
            (
                IntDataValue,
                [1, 2, 3, []],
                IncorrectListElementTypeError(
                    IncorrectTypeError("int", []), 3
                ),
            ),
            (
                StringDataValue,
                ["one", "two", "three", {}],
                IncorrectListElementTypeError(
                    IncorrectTypeError("string", {}), 3
                ),
            ),
            (
                data_list(StringDataValue),
                [["one", "two"], ["three"], ["four", 5]],
                IncorrectListElementTypeError(
                    IncorrectListElementTypeError(
                        IncorrectTypeError("string", 5), 1
                    ),
                    2,
                ),
            ),
        ),
    )
    def test_error(self, data_cls, val, error):
        with pytest.raises(type(error)) as e:
            data_list(data_cls).from_value(val)
        assert e.value.msg == error.msg


class ExampleNestedObject(DataObject):
    fields = [Field("string", StringDataValue), Field("integer", IntDataValue)]

    def __init__(self, *, string: str, integer: int):
        self.string = string
        self.integer = integer


class ExampleDataObject(DataObject):
    fields = [
        Field("string", StringDataValue),
        Field("string_opt", StringDataValue, required=False),
        Field("integer", IntDataValue),
        Field("integer_opt", IntDataValue, required=False),
        Field("obj", ExampleNestedObject),
        Field("obj_opt", ExampleNestedObject, required=False),
        Field("stringlist", data_list(StringDataValue)),
        Field("stringlist_opt", data_list(StringDataValue), required=False),
        Field("integerlist", data_list(IntDataValue)),
        Field("integerlist_opt", data_list(IntDataValue), required=False),
        Field("objlist", data_list(ExampleNestedObject)),
        Field("objlist_opt", data_list(ExampleNestedObject), required=False),
    ]

    def __init__(
        self,
        *,
        string: str,
        string_opt: Optional[str],
        integer: int,
        integer_opt: Optional[int],
        obj: ExampleNestedObject,
        obj_opt: Optional[ExampleNestedObject],
        stringlist: List[StringDataValue],
        stringlist_opt: Optional[List[StringDataValue]],
        integerlist: List[IntDataValue],
        integerlist_opt: Optional[List[IntDataValue]],
        objlist: List[ExampleNestedObject],
        objlist_opt: Optional[List[ExampleNestedObject]]
    ):
        self.string = string
        self.string_opt = string_opt
        self.integer = integer
        self.integer_opt = integer_opt
        self.obj = obj
        self.obj_opt = obj_opt
        self.stringlist = stringlist
        self.stringlist_opt = stringlist_opt
        self.integerlist = integerlist
        self.integerlist_opt = integerlist_opt
        self.objlist = objlist
        self.objlist_opt = objlist_opt


example_data_object_dict_no_optionals = {
    "string": "string",
    "integer": 1,
    "obj": {"string": "nestedstring", "integer": 2},
    "stringlist": ["one", "two"],
    "integerlist": [3, 4, 5],
    "objlist": [
        {"string": "nestedstring2", "integer": 6},
        {"string": "nestedstring3", "integer": 7},
    ],
}
example_data_object_dict_no_optionals_with_none = {
    "string": "string",
    "string_opt": None,
    "integer": 1,
    "integer_opt": None,
    "obj": {"string": "nestedstring", "integer": 2},
    "obj_opt": None,
    "stringlist": ["one", "two"],
    "stringlist_opt": None,
    "integerlist": [3, 4, 5],
    "integerlist_opt": None,
    "objlist": [
        {"string": "nestedstring2", "integer": 6},
        {"string": "nestedstring3", "integer": 7},
    ],
    "objlist_opt": None,
}
example_data_object_dict_with_optionals = {
    "string": "string",
    "string_opt": "string_opt",
    "integer": 1,
    "integer_opt": 11,
    "obj": {"string": "nestedstring", "integer": 2},
    "obj_opt": {"string": "nestedstring_opt", "integer": 22},
    "stringlist": ["one", "two"],
    "stringlist_opt": ["one_opt", "two_opt"],
    "integerlist": [3, 4, 5],
    "integerlist_opt": [33, 44, 55],
    "objlist": [
        {"string": "nestedstring2", "integer": 6},
        {"string": "nestedstring3", "integer": 7},
    ],
    "objlist_opt": [
        {"string": "nestedstring2_opt", "integer": 66},
        {"string": "nestedstring3_opt", "integer": 77},
    ],
}


class TestDataObject:
    def test_success_no_optionals(self):
        result = ExampleDataObject.from_dict(
            example_data_object_dict_no_optionals
        )
        assert result.string == "string"
        assert result.string_opt is None
        assert result.integer == 1
        assert result.integer_opt is None
        assert result.obj.string == "nestedstring"
        assert result.obj.integer == 2
        assert result.obj_opt is None
        assert result.stringlist == ["one", "two"]
        assert result.stringlist_opt is None
        assert result.integerlist == [3, 4, 5]
        assert result.integerlist_opt is None
        assert result.objlist[0].string == "nestedstring2"
        assert result.objlist[0].integer == 6
        assert result.objlist[1].string == "nestedstring3"
        assert result.objlist[1].integer == 7
        assert result.objlist_opt is None

    def test_success_with_optionals(self):
        result = ExampleDataObject.from_dict(
            example_data_object_dict_with_optionals
        )
        assert result.string == "string"
        assert result.string_opt == "string_opt"
        assert result.integer == 1
        assert result.integer_opt == 11
        assert result.obj.string == "nestedstring"
        assert result.obj.integer == 2
        assert result.obj_opt is not None
        assert result.obj_opt.string == "nestedstring_opt"
        assert result.obj_opt.integer == 22
        assert result.stringlist == ["one", "two"]
        assert result.stringlist_opt == ["one_opt", "two_opt"]
        assert result.integerlist == [3, 4, 5]
        assert result.integerlist_opt == [33, 44, 55]
        assert result.objlist[0].string == "nestedstring2"
        assert result.objlist[0].integer == 6
        assert result.objlist[1].string == "nestedstring3"
        assert result.objlist[1].integer == 7
        assert result.objlist_opt is not None
        assert result.objlist_opt[0].string == "nestedstring2_opt"
        assert result.objlist_opt[0].integer == 66
        assert result.objlist_opt[1].string == "nestedstring3_opt"
        assert result.objlist_opt[1].integer == 77

    @pytest.mark.parametrize(
        "val, error",
        (
            (
                {
                    "integer": 1,
                    "obj": {"string": "nestedstring", "integer": 2},
                    "stringlist": ["one", "two"],
                    "integerlist": [3, 4, 5],
                    "objlist": [
                        {"string": "nestedstring2", "integer": 6},
                        {"string": "nestedstring3", "integer": 7},
                    ],
                },
                IncorrectFieldTypeError(
                    IncorrectTypeError("StringDataValue", None), "string"
                ),
            ),
            (
                {
                    "string": "string",
                    "integer": "1",
                    "obj": {"string": "nestedstring", "integer": 2},
                    "stringlist": ["one", "two"],
                    "integerlist": [3, 4, 5],
                    "objlist": [
                        {"string": "nestedstring2", "integer": 6},
                        {"string": "nestedstring3", "integer": 7},
                    ],
                },
                IncorrectFieldTypeError(
                    IncorrectTypeError("int", "1"), "integer"
                ),
            ),
            (
                {
                    "string": "string",
                    "integer": 1,
                    "obj": {"string": 8, "integer": 2},
                    "stringlist": ["one", "two"],
                    "integerlist": [3, 4, 5],
                    "objlist": [
                        {"string": "nestedstring2", "integer": 6},
                        {"string": "nestedstring3", "integer": 7},
                    ],
                },
                IncorrectFieldTypeError(
                    IncorrectFieldTypeError(
                        IncorrectTypeError("string", 8), "string"
                    ),
                    "obj",
                ),
            ),
            (
                {
                    "string": "string",
                    "integer": 1,
                    "obj": {"string": "nestedstring", "integer": 2},
                    "stringlist": ["one", 2],
                    "integerlist": [3, 4, 5],
                    "objlist": [
                        {"string": "nestedstring2", "integer": 6},
                        {"string": "nestedstring3", "integer": 7},
                    ],
                },
                IncorrectFieldTypeError(
                    IncorrectListElementTypeError(
                        IncorrectTypeError("string", 2), 1
                    ),
                    "stringlist",
                ),
            ),
            (
                {
                    "string": "string",
                    "integer": 1,
                    "obj": {"string": "nestedstring", "integer": 2},
                    "stringlist": ["one", "two"],
                    "integerlist": [3, 4, 5],
                    "objlist": [
                        {"string": "nestedstring2", "integer": "6"},
                        {"string": "nestedstring3", "integer": 7},
                    ],
                },
                IncorrectFieldTypeError(
                    IncorrectListElementTypeError(
                        IncorrectFieldTypeError(
                            IncorrectTypeError("int", "6"), "integer"
                        ),
                        0,
                    ),
                    "objlist",
                ),
            ),
            ("string", IncorrectTypeError("dict", "string")),
            (1, IncorrectTypeError("dict", 1)),
            (True, IncorrectTypeError("dict", True)),
            ([], IncorrectTypeError("dict", [])),
        ),
    )
    def test_error(self, val, error):
        with pytest.raises(type(error)) as e:
            ExampleDataObject.from_value(val)
        assert e.value.msg == error.msg

    @pytest.mark.parametrize(
        "d",
        (
            example_data_object_dict_no_optionals,
            example_data_object_dict_with_optionals,
        ),
    )
    def test_dict_round_trip(self, d):
        assert d == ExampleDataObject.from_dict(d).to_dict(keep_none=False)

    def test_to_dict_keep_none(self):
        assert (
            example_data_object_dict_no_optionals_with_none
            == ExampleDataObject.from_dict(
                example_data_object_dict_no_optionals
            ).to_dict()
        )
