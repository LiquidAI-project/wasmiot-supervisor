"""General settings and variables for Wasm."""

from os import environ
from typing import Dict

from wasm_utils.wasm_api import ModuleConfig
from wasm_utils.wasmtime import WasmtimeRuntime
from wasm_utils.wasm3 import Wasm3Runtime


environ.setdefault("WASM_RUNTIME", "wasmtime")

WasmRuntimeType = Wasm3Runtime if environ["WASM_RUNTIME"] == "wasm3" else WasmtimeRuntime
print(f"Using {WasmRuntimeType.__name__} as WASM runtime.")

wasm_runtime: WasmRuntimeType = WasmRuntimeType()
wasm_modules: Dict[str, ModuleConfig] = {}