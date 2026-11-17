#!/usr/bin/env bash
# Build panda_h7 firmware the way the pinned panda SConscript does (DEBUG build), from a git revision of the
# sunnypilot tree.  usage: build_fw.sh <sunnypilot checkout> <rev> <name>
# Output: $PANDA_FW_DIR/out/<name>/{main.bin,panda_h7.bin.signed,main.elf}
set -euo pipefail
SP="$1"; REV="$2"; NAME="$3"
T="${PANDA_FW_DIR:?set PANDA_FW_DIR to a short path holding the unpacked toolchain in gcc/}"
GCC="$T/gcc/arm-gnu-toolchain-13.2.Rel1-mingw-w64-i686-arm-none-eabi/bin"
B="$T/b/$NAME"; OUT="$T/out/$NAME"
rm -rf "$B" "$OUT"; mkdir -p "$B" "$OUT"
# LF sources straight from git, not from the CRLF working copy
git -C "$SP" -c core.longpaths=true archive "$REV" panda/board opendbc_repo/opendbc/safety | tar xf - -C "$B"
cd "$B/panda"
INC_OPENDBC="$B/opendbc_repo"
hash4() { python -c "import sys,hashlib;print('0x%08XU' % int.from_bytes(hashlib.sha256(open(sys.argv[1],'rb').read().replace(b'\r',b'')).digest()[:4],'little'))" "$1"; }
HH=$(hash4 board/health.h); CH=$(hash4 "$INC_OPENDBC/opendbc/safety/can.h")
FLAGS="-mcpu=cortex-m7 -mhard-float -DSTM32H7 -DSTM32H725xx -Iboard/stm32h7/inc -mfpu=fpv5-d16 -DALLOW_DEBUG -DHEALTH_PACKET_VERSION=$HH -DCAN_PACKET_VERSION_HASH=$CH -Wall -Wextra -Wstrict-prototypes -Werror -mlittle-endian -mthumb -nostdlib -fno-builtin -std=gnu11 -fmax-errors=1 -Tboard/stm32h7/stm32h7x5_flash.ld -fsingle-precision-constant -Os -g"
mkdir -p o
"$GCC/arm-none-eabi-gcc.exe" $FLAGS -o o/startup.o -c board/stm32h7/startup_stm32h7x5xx.s
"$GCC/arm-none-eabi-gcc.exe" -o o/main.o -c $FLAGS -I. -Iboard/stm32h7/inc "-I$(cygpath -m "$INC_OPENDBC")" board/main.c
"$GCC/arm-none-eabi-gcc.exe" -o "$OUT/main.elf" -Wl,--section-start,.isr_vector=0x8020000 $FLAGS o/startup.o o/main.o
"$GCC/arm-none-eabi-objcopy.exe" -O binary "$OUT/main.elf" "$OUT/main.bin"
SETLEN=1 python board/crypto/sign.py "$(cygpath -m "$OUT/main.bin")" "$(cygpath -m "$OUT/panda_h7.bin.signed")" board/crypto/certs/debug >/dev/null
echo "$NAME ($REV): health $HH can $CH"
sha256sum "$OUT/main.bin" "$OUT/panda_h7.bin.signed" | sed "s#$T/##"
ls -la "$OUT" | awk '{print $5, $9}' | grep -E "bin|elf"
