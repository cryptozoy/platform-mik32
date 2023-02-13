# Copyright 2020-present PlatformIO <contact@platformio.org>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Custom 

get from

https://github.com/espressif/esp-idf
"""

import copy
import json
import subprocess
import sys
import os
import ctypes

from os.path import join, isdir

import click
import semantic_version

from SCons.Script import (
    ARGUMENTS,
    COMMAND_LINE_TARGETS,
    DefaultEnvironment,
)

from platformio import fs
from platformio.proc import exec_command
from platformio.util import get_systype
from platformio.builder.tools.piolib import ProjectAsLibBuilder
from platformio.package.version import get_original_version, pepver_to_semver

env = DefaultEnvironment()
# env.SConscript("_embed_files.py", exports="env")

env.SConscript("_bare.py")

platform = env.PioPlatform()
board = env.BoardConfig()

TOOLCHAIN_DIR = platform.get_package_dir(
    "framework-mik32v0-sdk"
)

assert isdir(TOOLCHAIN_DIR)

BUILD_DIR = env.subst("$BUILD_DIR")
PROJECT_DIR = env.subst("$PROJECT_DIR")
PROJECT_SRC_DIR = env.subst("$PROJECT_SRC_DIR")
CMAKE_API_REPLY_PATH = join(".cmake", "api", "v1", "reply")

SHARED_DIR = join(TOOLCHAIN_DIR, "shared")
LDSCRIPTS_DIR = join(SHARED_DIR, "ldscripts")
RUNTIME_DIR = join(SHARED_DIR, "runtime")
HAL_DIR = join(TOOLCHAIN_DIR, "hal")


def log(msg, should_append=False):
    LOG_FILE = join(PROJECT_DIR, "log.log")

    with open(LOG_FILE, 'a' if should_append else 'w') as f:
        f.write(msg + '\n')


env.AppendUnique(
    CPPPATH=[
        '-v',
        "$PROJECT_SRC_DIR",
        join(SHARED_DIR, "include"),
        join(SHARED_DIR, "periphery"),
        join(SHARED_DIR, "runtime"),
        join(HAL_DIR, "core", "Include"),
        join(HAL_DIR, "peripherals", "Include"),
    ],
    LINKFLAGS=[
        "-nostartfiles",
    ],
    LIBS=[
        "c"
    ]
)

if not env.BoardConfig().get("build.ldscript", ""):
    env.Replace(
        LDSCRIPT_PATH=join(SHARED_DIR, "ldscripts", board.get(
            "build.mik32v0-sdk.ldscript"))
    )

libs = [
    env.BuildLibrary(
        join("$BUILD_DIR", "runtime"),
        join(SHARED_DIR, "runtime"),
    ),
    env.BuildLibrary(
        join("$BUILD_DIR", "libs"),
        join(SHARED_DIR, "libs"),
    ),
    env.BuildLibrary(
        join("$BUILD_DIR", "hal_core"),
        join(HAL_DIR, "core", "Source"),
    ),
    env.BuildLibrary(
        join("$BUILD_DIR", "hal_peripherals"),
        join(HAL_DIR, "peripherals", "Source"),
    ),
]

env.Prepend(LIBS=libs)
