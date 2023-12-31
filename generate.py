#!/usr/bin/env python3

import re
import shutil
import subprocess
import sys

# Additional required flags for MinGW headers
# https://github.com/0x6d696368/ghidra-data/tree/master/typeinfo#how-was-winapi_32gdt-generated
MINGW_OPTIONS = [
    '-DCONST="const"',
    '-D__restrict__=""',
    '-D__always_inline__="inline"',
    '-D__gnu_inline__="inline"',
    '-D__builtin_va_list="void *"',
]

# Default options from generic_clib_32.prf
DEFAULT_OPTIONS_32 = [
    '-D_X86_',
    '-D__STDC__',
    '-D_GNU_SOURCE',
    '-D__WORDSIZE=32',
    '-D__builtin_va_list=void *',
    '-D__DO_NOT_DEFINE_COMPILE',
    '-D_Complex',
    '-D__NO_STRING_INLINES',
    '-D__NO_LONG_DOUBLE_MATH',
    '-D__signed__',
    '-D__extension__=""',
    '-D__GLIBC_HAVE_LONG_LONG=1',
    '-Daligned_u64=uint64_t',
]

# Default options from generic_clib_64.prf
DEFAULT_OPTIONS_64 = [
    '-D_X86_',
    '-D__STDC__',
    '-D_GNU_SOURCE',
    '-D__WORDSIZE=64',
    '-D__builtin_va_list=void *',
    '-D__DO_NOT_DEFINE_COMPILE',
    '-D_Complex',
    '-D__NO_STRING_INLINES',
    '-D__signed__',
    '-D__extension__=""',
    '-D__GLIBC_HAVE_LONG_LONG=1',
    '-D__need_sigset_t',
    '-Daligned_u64=uint64_t',
]

# Default GCC flags
GCC_FLAGS = [
    '-std=c99',
    '-I.',
]

# Default source
DEFAULT_SOURCE="""
// This file was generated by https://github.com/hkva/ghidra-directx-data

// BEGIN MANUAL DEFINITIONS

typedef struct _Float16 {
    float m[16];
} _Float16;

typedef unsigned short __bf16;

// END MANUAL DEFINITIONS

"""

# Helper: Make sure a system command is available
def require_command(cmd):
    if shutil.which(cmd) is None:
        print(f'!!! System is missing required command {cmd}')
        exit(1)

def process_source(source):
    # No __asm__
    source = re.sub(r'__asm__ .*\(.*\);', '(void)123; /* GHIDRA: Removed __asm__ statement */', source)
    # No __int128
    source = re.sub(r'(__int128)', 'long /* GHIDRA: Removed __int128 */', source)
    # No float16 specifier
    source = re.sub(r'(\.0f16)', '.0f /* GHIDRA: Removed f16 */', source)
    return source

def run_gcc(gcc, flags, input, capture_stderr = False):
    p = subprocess.Popen([gcc] + GCC_FLAGS + flags + ['-'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
    s_out, s_err = p.communicate(input=input.encode())
    if p.returncode != 0:
        print(f'GCC command failed: {s_err.decode()}')
        exit(1)
    return s_err.decode() if capture_stderr else s_out.decode()


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print(f'Usage: {sys.argv[0]} <target> <32|64>')
        exit(1)

    a_name = sys.argv[1]
    a_arch = sys.argv[2]

    if a_arch != '32' and a_arch != '64':
        print('Architecture must be either 32 or 64')
        exit(1)
    print(f'Generating profile {a_name} ({a_arch}-bit)')

    gcc_cmd = 'x86_64-w64-mingw32-gcc' if a_arch == '64' else 'i686-w64-mingw32-gcc'

    # Generate flattened header
    print('Processing sources...')
    with open(f'{a_name}_{a_arch}.h', 'w') as f:
        f.write(DEFAULT_SOURCE)
        f.write(process_source(run_gcc(gcc_cmd, ['-P', '-E'], f'#include <{a_name}.h>')))
        

    # Generate parser options
    print('Generating parser options...')
    with open(f'{a_name}_{a_arch}_parser_options.txt', 'w') as f:
        opts = MINGW_OPTIONS
        opts += DEFAULT_OPTIONS_64 if a_arch == 'x64' else DEFAULT_OPTIONS_32

        empty_file = " /* :) */ "
        # Compile empty file to get include paths
        out = run_gcc(gcc_cmd, ['-xc', '-E', '-v'], empty_file, True).splitlines()
        opts += [ f'-I{inc.strip()}' for inc in out[out.index('#include <...> search starts here:')+1:out.index('End of search list.')] ]
        # Compile empty file to get preprocessor definitions
        out = run_gcc(gcc_cmd, ['-dM', '-E'], empty_file).splitlines()
        for i in out:
            m = re.search(r'#define ([^ ]*) (.*)', i)
            opts.append(f'-D{m[1]}="{m[2]}"')

        for opt in opts:
            f.write(f'{opt}\n')