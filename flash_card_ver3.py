#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Flashcard (TXT version)
- 한 줄:  단어\뜻\[결과]
  * 결과: 1(맞춤) / 0(틀림)  — 없으면 학습 미진행
- Space   : 답 보기 토글
- → / ←    : 다음 / 이전 카드
- A / S   : 정답 / 오답 기록
"""

import tkinter as tk
from tkinter import filedialog, messagebox
import json, random, pathlib, datetime

DELIM = "\\"               # 줄 구분자
PROGRESS_FILE = "progress.json"  # 학습률·SM-2 이력 저장

class FlashcardApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Flashcards (TXT)")
        self.geometry("600x380")        # 창 크기 키움
        self.resizable(False, False)

        self.cards: list[dict] = []     # [{'word':, 'meaning':, 'ef':, 'due':, 'result':}]
        self.index = -1                 # 현재 카드 인덱스
        self.show_answer = False

        # ---------- UI ----------
        self.lbl = tk.Label(self, text="파일을 열어주세요", font=("Helvetica", 24))
        self.lbl.pack(expand=True, pady=40)

        btn_f = tk.Frame(self)
        btn_f.pack(pady=5)
        self.btn_prev = tk.Button(btn_f, text="← 이전", width=10, command=self.prev_card, state=tk.DISABLED)
        self.btn_prev.pack(side="left", padx=4)
        self.btn_show = tk.Button(btn_f, text="Space: 정답 보기", width=18,
                                  command=self.toggle_answer, state=tk.DISABLED)
        self.btn_show.pack(side="left", padx=4)
        self.btn_next = tk.Button(btn_f, text="다음 →", width=10, command=self.next_card, state=tk.DISABLED)
        self.btn_next.pack(side="left", padx=4)

        grade_f = tk.Frame(self)
        grade_f.pack(pady=5)
        self.btn_correct = tk.Button(grade_f, text="A: 정답(1)", width=12,
                                     command=lambda: self.grade_card(True), state=tk.DISABLED)
        self.btn_correct.pack(side="left", padx=4)
        self.btn_wrong = tk.Button(grade_f, text="S: 오답(0)", width=12,
                                   command=lambda: self.grade_card(False), state=tk.DISABLED)
        self.btn_wrong.pack(side="left", padx=4)

        self.lbl_prog = tk.Label(self, text="")
        self.lbl_prog.pack(pady=4)

        menu = tk.Menu(self)
        f_menu = tk.Menu(menu, tearoff=0)
        f_menu.add_command(label="열기(txt)…", command=self.open_file)
        f_menu.add_command(label="다시 시작", command=self.restart_session, state=tk.DISABLED)
        f_menu.add_separator()
        f_menu.add_command(label="종료", command=self.quit)
        menu.add_cascade(label="파일", menu=f_menu)
        self.config(menu=menu)

        # ---------- 단축키 ----------
        self.bind("<space>", lambda e: self.toggle_answer())
        self.bind("<Right>", lambda e: self.next_card())
        self.bind("<Left>", lambda e: self.prev_card())
        self.bind("<Key-a>", lambda e: self.grade_card(True))
        self.bind("<Key-s>", lambda e: self.grade_card(False))

    # ---------------- 파일 처리 ----------------
    def open_file(self):
        path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt")])
        if not path:
            return
        self.file_path = pathlib.Path(path)
        try:
            self.cards = self._load_txt(self.file_path)
        except Exception as e:
            messagebox.showerror("읽기 오류", str(e))
            return

        random.shuffle(self.cards)
        self.index = -1
        self.next_card(first=True)

        # 메뉴·버튼 활성
        for b in (self.btn_show, self.btn_next, self.btn_prev,
                  self.btn_correct, self.btn_wrong):
            b.config(state=tk.NORMAL)
        self.config(menu=None)  # 메뉴 갱신
        self.__init_menu(restart_enabled=True)

    def _load_txt(self, path: pathlib.Path):
        cards = []
        with path.open(encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                parts = line.rstrip("\n").split(DELIM)
                if len(parts) < 2:
                    continue
                word, meaning = parts[0].strip(), parts[1].strip()
                result = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else None
                cards.append({"word": word, "meaning": meaning,
                              "ef": 2.5, "due": 0, "result": result})
        return cards

    # ---------------- 학습 로직 ----------------
    def next_card(self, first=False):
        if not first:
            self.index += 1
        if self.index >= len(self.cards):
            self.lbl.config(text="학습 끝 🎉")
            return
        self.show_answer = False
        self._render()

    def prev_card(self):
        if self.index <= 0:
            return
        self.index -= 1
        self.show_answer = False
        self._render()

    def toggle_answer(self):
        if self.index == -1:
            return
        self.show_answer = not self.show_answer
        self._render()

    def grade_card(self, correct: bool):
        if self.index == -1:
            return
        self.cards[self.index]['result'] = int(correct)
        self._save_txt()               # 즉시 덮어쓰기
        self.next_card()

    # ---------------- SM-2 간단 적용 (선택사항 추가 구현 가능) ----------------
    # 여기서는 EF 값·due 날짜 계산 로직만 자리만 마련, 실제 사용은 필요시 확장

    # ---------------- 기타 ----------------
    def _render(self):
        card = self.cards[self.index]
        text = card['meaning'] if self.show_answer else card['word']
        self.lbl.config(text=text)
        self.lbl_prog.config(text=f"{self.index+1}/{len(self.cards)}")

    def _save_txt(self):
        """현재 cards 리스트를 그대로 txt로 재기록"""
        lines = [f"{c['word']}{DELIM}{c['meaning']}"
                 f"{DELIM}{c['result']}" if c['result'] is not None else
                 f"{c['word']}{DELIM}{c['meaning']}"
                 for c in self.cards]
        self.file_path.write_text("\n".join(lines), encoding="utf-8")

    def restart_session(self):
        random.shuffle(self.cards)
        self.index = -1
        self.next_card(first=True)

    def __init_menu(self, restart_enabled=False):
        menu = tk.Menu(self)
        f_menu = tk.Menu(menu, tearoff=0)
        f_menu.add_command(label="열기(txt)…", command=self.open_file)
        f_menu.add_command(label="다시 시작", command=self.restart_session,
                           state=(tk.NORMAL if restart_enabled else tk.DISABLED))
        f_menu.add_separator()
        f_menu.add_command(label="종료", command=self.quit)
        menu.add_cascade(label="파일", menu=f_menu)
        self.config(menu=menu)

if __name__ == "__main__":
    FlashcardApp().mainloop()
