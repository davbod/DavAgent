"""
tools/__init__.py

Auto-discovers all tool modules in this package. To add a new tool:
  1. Create a new .py file in this directory (e.g. my_tool.py)
  2. Define your function(s) in it
  3. Export a TOOLS dict: TOOLS = {"function_name": function}

That's it — no changes needed anywhere else.
"""
import importlib
import pkgutil

AVAILABLE_TOOLS = {}

for module_info in pkgutil.iter_modules(__path__):
    module = importlib.import_module(f".{module_info.name}", package=__name__)
    if hasattr(module, "TOOLS"):
        AVAILABLE_TOOLS.update(module.TOOLS)
