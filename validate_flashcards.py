#!/usr/bin/env python3
"""
검증 스크립트: 각 .txt 파일의 모든 행에 백슬래시(\\)가 정확히 한 개만 있는지 확인
사용법: python validate_flashcards.py /path/to/정처기공부파일
"""
from pathlib import Path
import sys
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s | %(message)s",
)

def validate_file(path: Path) -> bool:
    """파일 한 개를 검증하고, 실패 시 상세 로그를 남깁니다."""
    ok = True
    with path.open(encoding="utf-8") as f:
        for idx, line in enumerate(f, start=1):
            # 비어있는 줄 (공백 포함)은 검사 대상에서 제외
            if line.strip() == "":
                continue

            count = line.count("\\")
            if count != 1:
                logging.warning(
                    f"[{path.name}] {idx}번째 줄 → '\\' 갯수: {count} (내용: {line.rstrip()!r})"
                )
                ok = False
    return ok


def main(root: Path) -> None:
    txt_files = list(root.rglob("*.txt"))
    if not txt_files:
        logging.error("검증할 .txt 파일이 없습니다.")
        sys.exit(1)

    failed, passed = [], []
    for file in txt_files:
        if validate_file(file):
            passed.append(file)
        else:
            failed.append(file)

    logging.info(f"총 {len(txt_files)}개 중 ✅ {len(passed)}개 통과, ❌ {len(failed)}개 실패")
    if failed:
        logging.warning("실패한 파일 목록:")
        for f in failed:
            logging.warning(f"- {f.relative_to(root)}")
        sys.exit(2)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("사용법: python validate_flashcards.py /path/to/정처기 공부파일")
        sys.exit(1)
    main(Path(sys.argv[1]).expanduser().resolve())
