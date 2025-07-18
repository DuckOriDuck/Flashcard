#!/usr/bin/env python3
"""
변환 스크립트: '단어\\의미'를 '의미\\단어'로 바꾼 뒤 새로운 디렉터리에 저장
사용법: python transform_flashcards.py /path/to/정처기공부파일
"""
from pathlib import Path
import sys
import logging
from validate_flashcards import validate_file

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s | %(message)s",
)

def transform_line(line: str) -> str:
    line = line.rstrip("\n")
    if line.strip() == "":
        return "\n"  # 빈 줄은 그대로 반환
    try:
        left, right = line.split("\\", maxsplit=1)
        return f"{right}\\{left}\n"
    except ValueError:
        logging.warning(f"⚠️ 변환 실패 (\\ 없음): {line!r}")
        return line + "\n"

def process_file(src: Path, dst_root: Path) -> None:
    dst_path = dst_root / src.relative_to(src.parents[1])
    dst_path.parent.mkdir(parents=True, exist_ok=True)

    with src.open(encoding="utf-8") as r, dst_path.open("w", encoding="utf-8") as w:
        for line in r:
            transformed = transform_line(line)
            w.write(transformed)

    logging.info(f"✔️ {src.name} → {dst_path.relative_to(dst_root.parent)}")

def main(root: Path) -> None:
    dst_root = root.parent / f"{root.name}reverse"
    dst_root.mkdir(exist_ok=True)

    for txt_file in root.rglob("*.txt"):
        if validate_file(txt_file):
            process_file(txt_file, dst_root)
        else:
            logging.error(f"⚠️  검증 실패 → 변환 건너뜀: {txt_file}")
    logging.info(f"✅ 변환 완료. 결과 디렉터리: {dst_root}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("사용법: python transform_flashcards.py /path/to/정처기공부파일")
        sys.exit(1)
    main(Path(sys.argv[1]).expanduser().resolve())
