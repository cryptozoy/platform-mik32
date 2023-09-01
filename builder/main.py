# Copyright 2014-present PlatformIO <contact@platformio.org>
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

from os.path import join
from os.path import realpath

from SCons.Script import (ARGUMENTS, COMMAND_LINE_TARGETS, AlwaysBuild,
                          Builder, Default, DefaultEnvironment)


env = DefaultEnvironment()
env.SConscript("compat.py", exports="env")
platform = env.PioPlatform()
board = env.BoardConfig()

env.Replace(
    AR="riscv64-unknown-elf-gcc-ar",
    AS="riscv64-unknown-elf-as",
    CC="riscv64-unknown-elf-gcc",
    LD="riscv64-unknown-elf-ld",
    GDB="riscv64-unknown-elf-gdb",
    CXX="riscv64-unknown-elf-g++",
    OBJCOPY="riscv64-unknown-elf-objcopy",
    RANLIB="riscv64-unknown-elf-gcc-ranlib",
    SIZETOOL="riscv64-unknown-elf-size",

    ARFLAGS=["rc"],

    SIZEPRINTCMD='$SIZETOOL -d $SOURCES',

    PROGSUFFIX=".elf"
)

# Allow user to override via pre:script
if env.get("PROGNAME", "program") == "program":
    env.Replace(PROGNAME="firmware")

env.Append(
    BUILDERS=dict(
        ElfToHex=Builder(
            action=env.VerboseAction(" ".join([
                "$OBJCOPY",
                "-O",
                "ihex",
                "$SOURCES",
                "$TARGET"
            ]), "Building $TARGET"),
            suffix=".hex"
        ),
        ElfToBin=Builder(
            action=env.VerboseAction(" ".join([
                "$OBJCOPY",
                "-O",
                "binary",
                "$SOURCES",
                "$TARGET"
            ]), "Building $TARGET"),
            suffix=".bin"
        ),
    )
)

if not env.get("PIOFRAMEWORK"):
    env.SConscript("frameworks/_bare.py", exports="env")

env.SConscript("frameworks/custom.py", exports={"env": env})

#
# Target: Build executable and linkable firmware
#

target_elf = None
if "nobuild" in COMMAND_LINE_TARGETS:
    target_elf = join("$BUILD_DIR", "${PROGNAME}.elf")
    target_hex = join("$BUILD_DIR", "${PROGNAME}.hex")
    target_bin = join("$BUILD_DIR", "${PROGNAME}.bin")
else:
    target_elf = env.BuildProgram()
    target_hex = env.ElfToHex(join("$BUILD_DIR", "${PROGNAME}"), target_elf)
    target_bin = env.ElfToBin(join("$BUILD_DIR", "${PROGNAME}"), target_elf)
    env.Depends(target_hex, "checkprogsize")

AlwaysBuild(env.Alias("nobuild", target_hex))
target_buildprog = env.Alias("buildprog", target_hex, target_hex)
target_buildbin = env.Alias("buildbin", target_bin, target_bin)

#
# Target: Print binary size
#

target_size = env.Alias(
    "size", target_elf,
    env.VerboseAction("$SIZEPRINTCMD", "Calculating size $SOURCE"))
AlwaysBuild(target_size)

#
# Target: Upload by default .bin file
#

debug_tools = board.get("debug.tools", {})

openocd_dir = platform.get_package_dir("tool-openocd")

framework_name = env.GetProjectOption("framework")[0]
sdk_dir = platform.get_package_dir(framework_name)

upload_protocol = env.subst("$UPLOAD_PROTOCOL")
upload_actions = []
upload_target = target_hex
upload_speed = env.GetProjectOption("upload_speed", 500)
upload_command = env.GetProjectOption("upload_command", "")
upload_flags = env.GetProjectOption("upload_flags", [])

hex_path = target_hex[0].rstr().replace('\\', '/')

openocd_path = join(openocd_dir or "", "bin", "openocd.exe")
openocd_scripts = realpath(join(openocd_dir, 'openocd/scripts/'))

mik32_uploader_path = platform.get_package_dir("tool-mik32-uploader") or ""
mik32_uploader_exec = join(mik32_uploader_path, "mik32_upload.py")
openocd_target = realpath(join(
    mik32_uploader_path, "openocd-scripts/target/mik32.cfg"))

mik32_uploader_args = [
    hex_path, 
    "--openocd-exec", openocd_path, 
    "--adapter-speed", upload_speed,
    "--openocd-scripts", openocd_scripts,
    "--openocd-target", openocd_target,
    "--run-openocd",
]


openocd_supported_interfaces = [
    "mikron-link",
    "olimex-arm-usb-ocd",
    "olimex-arm-usb-ocd-h",
    "olimex-arm-usb-tiny-h",
    "olimex-jtag-tiny",
    "jlink",
    "altera-usb-blaster",
    "sipeed-rv-debugger",
]


if upload_protocol in openocd_supported_interfaces:
    env.Replace(
        UPLOADER=mik32_uploader_exec,
        UPLOADERFLAGS=[
            *mik32_uploader_args,
            "--openocd-interface", platform.get_interface_config_path(upload_protocol),
        ],
        UPLOADCMD='"$PYTHONEXE" "$UPLOADER" $UPLOADERFLAGS'
    )
    upload_actions = [env.VerboseAction("$UPLOADCMD", "Uploading $SOURCE")]

elif upload_protocol == "custom":
    env.Replace(
        UPLOADER=upload_command,
        UPLOADERFLAGS=upload_flags,
        UPLOADCMD="%s" % (upload_command),
    )
    # print("%s %s" % (upload_command, *upload_flags))
    upload_actions = [env.VerboseAction("$UPLOADCMD", "Uploading $SOURCE")]

else:
    print("Upload protocol %s not supported" % upload_protocol)

AlwaysBuild(env.Alias("upload", upload_target, upload_actions))

#
# Setup default targets
#

Default([target_buildprog, target_size])
