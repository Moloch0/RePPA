from __future__ import annotations

import os
from pathlib import Path
import sys

from pybind11.setup_helpers import Pybind11Extension, build_ext
from setuptools import setup


PROJECT_ROOT = Path(__file__).resolve().parent
TOOLCHAIN_BIN = Path(sys.prefix) / "bin"
ENVIRONMENT_CC = TOOLCHAIN_BIN / "x86_64-conda-linux-gnu-cc"
ENVIRONMENT_CXX = TOOLCHAIN_BIN / "x86_64-conda-linux-gnu-c++"
if ENVIRONMENT_CC.is_file() and ENVIRONMENT_CXX.is_file():
    os.environ["CC"] = str(ENVIRONMENT_CC)
    os.environ["CXX"] = str(ENVIRONMENT_CXX)


setup(
    ext_modules=[
        Pybind11Extension(
            "rootpart._core",
            [
                "rootpart/src/module.cpp",
                "rootpart/src/problem.cpp",
                "rootpart/src/rpr.cpp",
            ],
            include_dirs=[
                "rootpart/include",
                str(Path(sys.prefix) / "include"),
            ],
            extra_compile_args=["-O3", "-fopenmp"],
            extra_link_args=["-fopenmp"],
            cxx_std=20,
        )
    ],
    cmdclass={"build_ext": build_ext},
    zip_safe=False,
)
