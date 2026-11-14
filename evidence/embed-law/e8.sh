#!/bin/zsh
# E8 end to end: copy this harness byte for byte into a fresh folder, run its one command (reproduce.sh) there, then
# compare every number with the record. The record (this folder) is only read.
#     zsh ~/neos/sandbox/embed_law/e8.sh [OUT]          OUT defaults to ~/neos/sandbox/embed_law_e8
set -e; setopt pipefail
SRC=${0:A:h}
OUT=${1:-$SRC/../embed_law_e8}; OUT=${OUT:A}
[ -e "$OUT" ] && { echo "$OUT already exists; remove it or name another folder"; exit 1; }
python3 -I "$SRC/e8_compare.py" --precheck "$SRC"
FILES=(PROTOCOL.md HASHES.txt reproduce.sh e8.sh e8_compare.py stage1.py stage1b.py stage1d.py l1_reference.py build_maps.py
       gates.py e4_e3.py e6.py e7.py verify_wiring.py analyze.py laws/strict_author.py laws/author_laws.py laws/author_whole.py
       laws/author_tau.py)
mkdir -p "$OUT/laws" "$OUT/runs"
for f in $FILES; do cp "$SRC/$f" "$OUT/$f"; cmp -s "$SRC/$f" "$OUT/$f" || { echo "COPY DIFFERS: $f"; exit 1; }; done
echo "E8: record $SRC -> regeneration $OUT ($#FILES files copied byte for byte)"
zsh "$OUT/reproduce.sh"
sleep 2                                                   # let reproduce.sh's log writer finish
python3 -I "$OUT/e8_compare.py" "$SRC" "$OUT"
