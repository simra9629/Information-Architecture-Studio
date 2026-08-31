"""
Auto-discovery registry: scans a package directory and collects every
module's CONFIG dict, keyed by module name. This is what makes the system
scalable — adding a new genre, subgenre, or food mood is just adding one
small file to the right folder; nothing here or in the engine needs to
change.

Two loaders:
  load_configs      — flat: every .py file directly in the folder is one
                       entry (used by nonfiction/, modifiers/, food/).
  load_nested_configs — recursive: supports fiction/<genre>/<subgenre>.py.
                       A genre folder's own _base.py (if present) becomes
                       the top-level entry for that genre; every other file
                       in the folder becomes "<genre>/<subgenre>".
"""

import importlib
import os
import pkgutil


def load_configs(package_name: str, package_path) -> dict:
    configs = {}
    for _finder, name, ispkg in pkgutil.iter_modules(package_path):
        if ispkg or name.startswith("_"):
            continue
        module = importlib.import_module(f"{package_name}.{name}")
        if hasattr(module, "CONFIG"):
            configs[name] = module.CONFIG
    return configs


def load_nested_configs(package_name: str, package_path) -> dict:
    configs = {}
    for _finder, name, ispkg in pkgutil.iter_modules(package_path):
        if name.startswith("_"):
            continue
        if ispkg:
            sub_path = [os.path.join(package_path[0], name)]
            full_name = f"{package_name}.{name}"
            # The subfolder's own _base.py (the parent genre's general
            # config) becomes the top-level entry for that genre name.
            try:
                base_module = importlib.import_module(f"{full_name}._base")
                if hasattr(base_module, "CONFIG"):
                    configs[name] = base_module.CONFIG
            except ModuleNotFoundError:
                pass
            # Every other file in the subfolder is a specific subgenre.
            for leaf_name, leaf_cfg in load_configs(full_name, sub_path).items():
                configs[f"{name}/{leaf_name}"] = leaf_cfg
        else:
            module = importlib.import_module(f"{package_name}.{name}")
            if hasattr(module, "CONFIG"):
                configs[name] = module.CONFIG
    return configs

