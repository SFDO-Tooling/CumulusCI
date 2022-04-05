import json
import pathlib
import typing as T
from abc import ABCMeta

from wasmer import Instance, Module, Store, engine
from wasmer_compiler_llvm import Compiler

from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.new_tasks.registry import task

eng = engine.Universal(Compiler)
store = Store(eng)


def to_wasm_string(instance: Instance, string: str) -> T.Tuple[int, int]:
    bytestring = string.encode("utf-8")
    size = len(bytestring)
    buffer_location = instance.exports.allocate(size)
    view = instance.exports.memory.uint8_view()

    for (i, b) in enumerate(bytestring):
        view[buffer_location + i] = b

    return (buffer_location, size)


def from_wasm_string(instance: Instance, location: int, length: int) -> str:
    bytestring = instance.exports.memory.uint8_view()[location : location + length]
    return bytestring.decode("utf-8")


def load_wasm_module(wasm_module: pathlib.Path):
    # klass = create_wasm_class(wasm_module, "test")
    # task()
    pass


def create_wasm_class(wasm_module: pathlib.Path, name: str) -> T.Type:
    module = Module(
        store,
        wasm_module.read_bytes(),
    )
    return type(name, (WasmTask,), {"module": module})


class WasmTask(metaclass=ABCMeta):
    instance: Instance
    options: int

    def __new__(cls):
        ret = object.__new__(cls)
        ret.instance = Instance(cls.module)
        return ret

    def __init__(self, options: dict):
        options_string = json.dumps(options)

        self.options = self.parse_dynamic_options(options_string)
        # TODO: freezing
        if self.options == 0:
            self.options = self.parse_options(options_string)

        if self.options == 0:
            raise TaskOptionsError("Unable to parse task options")

    def get_task_id(self) -> str:
        return from_wasm_string(self.instance, *self.instance.exports.get_task_id())

    def parse_options(self, json: str) -> int:
        return self.instance.exports.parse_options(*to_wasm_string(self.instance, json))

    def parse_dynamic_options(self, json: str) -> int:
        return self.instance.exports.parse_dynamic_options(
            *to_wasm_string(self.instance, json)
        )

    def run(self) -> int:
        return self.instance.exports.run_task(self.options)
