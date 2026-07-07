from __future__ import annotations

from collections.abc import Mapping


JsonPrimitive = str | int | float | bool | None
JsonMutableValue = JsonPrimitive | dict[str, "JsonMutableValue"] | list["JsonMutableValue"]
JsonMutableObject = dict[str, JsonMutableValue]
JsonFrozenValue = JsonPrimitive | Mapping[str, "JsonFrozenValue"] | tuple["JsonFrozenValue", ...]
JsonFrozenObject = Mapping[str, JsonFrozenValue]

