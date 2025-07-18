"""
Flashcards (Advanced v2)
=======================
요구사항
----------
1. 핫키
   * **스페이스바** : 정답 토글
   * **→ (Right)**  : 다음 카드
   * **← (Left)**  : 이전 카드
   * **A** : 정답 (quality 5)
   * **S** : 오답 (quality 2)
2. 덱을 다 끝낸 뒤 즉시 *재시작* 가능한 버튼 추가
3. CSV 세 번째 열(선택) — 1 = 맞춤, 0 = 틀림. 없는 경우 실행 중 에러 없이 동작하며, 결과를 저장 시 자동 추가/업데이트.
4. 셔플 모드 — 덱 로딩 시 무작위 섞기. 같은 세션에서 중복 노출 없음.
5. (옵션) 카드 리스트 확인 모달  : F1 핫키.
6. 윈도우 크기 확대(640×420), 폰트 가독성 개선.

코드
----
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import os
import random
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Dict, List, Tuple

######################## Internationalisation ###############################
LANG_DATA = {
    "ko": {
        "file": "파일",
        "open": "열기…",
        "exit": "종료",
        "correct": "맞췄음 ✓",
        "wrong": "틀렸음 ✗",
        "show": "정답 보기",
        "next": "다음 카드",
        "prev": "이전 카드",
        "restart": "재시작",
        "progress": "진행률: {done}/{total} ({pct:.0%})",
        "finished": "학습 완료! 재시작 버튼을 눌러주세요.",
        "no_file": "CSV 파일을 열어주세요",
        "menu_lang": "언어",
        "lang_ko": "한국어",
        "lang_en": "English",
        "error_read": "파일을 읽지 못했습니다",
        "list_title": "카드 리스트",
    },
    "en": {
        "file": "File",
        "open": "Open…",
        "exit": "Exit",
        "correct": "Correct ✓",
        "wrong": "Wrong ✗",
        "show": "Show Answer",
        "next": "Next Card",
        "prev": "Previous Card",
        "restart": "Restart",
        "progress": "Progress: {done}/{total} ({pct:.0%})",
        "finished": "All cards finished! Hit Restart.",
        "no_file": "Please open a CSV file",
        "menu_lang": "Language",
        "lang_ko": "Korean",
        "lang_en": "English",
        "error_read": "Could not read file",
        "list_title": "Card List",
    },
}
###############################################################################
PROG_FILE = "progress.json"

######################## Spaced‑Repetition (SM‑2) ############################

def sm2_update(ef: float, interval: int, reps: int, quality: int) -> Tuple[float, int, int]:
    """Return new (ef, interval, reps) based on quality (0–5)."""
    if quality < 3:
        reps = 0
        interval = 1
    else:
        if reps == 0:
            interval = 1
        elif reps == 1:
            interval = 6
        else:
            interval = round(interval * ef)
        reps += 1
    ef = max(1.3, ef + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)))
    return ef, interval, reps

class CardStats:
    def __init__(self, ef: float = 2.5, interval: int = 0, reps: int = 0, next_due: str | None = None):
        self.ef = ef
        self.interval = interval
        self.reps = reps
        self.next_due = dt.date.fromisoformat(next_due) if next_due else dt.date.today()

    def to_json(self):
        return {
            "ef": self.ef,
            "interval": self.interval,
            "reps": self.reps,
            "next_due": self.next_due.isoformat(),
        }

    @classmethod
    def from_json(cls, data):
        return cls(data["ef"], data["interval"], data["reps"], data["next_due"])

######################## Main Application ####################################
class FlashcardApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.lang = "ko"
        self.title("Flashcards")
        self.geometry("640x420")
        self.resizable(False, False)

        # Data
        self.csv_path: Path | None = None
        self.cards: List[Tuple[str, str]] = []          # (word, meaning)
        self.stats: Dict[str, CardStats] = {}
        self.results: Dict[str, int] = {}                # 1 = correct, 0 = wrong
        self.deck: List[Tuple[str, str]] = []            # shuffled list (today‑due)
        self.idx: int = -1                               # pointer in deck
        self.showing_answer = False

        # ---------- UI ----------
        self.lbl_text = tk.Label(self, text=self._t("no_file"), font=("Helvetica", 26), wraplength=600, justify="center")
        self.lbl_text.pack(expand=True, pady=15)

        btn_bar = tk.Frame(self)
        btn_bar.pack(pady=5)

        self.btn_prev = tk.Button(btn_bar, text=self._t("prev"), width=10, command=self.prev_card, state=tk.DISABLED)
        self.btn_prev.pack(side="left", padx=4)

        self.btn_show = tk.Button(btn_bar, text=self._t("show"), width=12, command=self.toggle_answer, state=tk.DISABLED)
        self.btn_show.pack(side="left", padx=4)

        self.btn_next = tk.Button(btn_bar, text=self._t("next"), width=10, command=self.next_card, state=tk.DISABLED)
        self.btn_next.pack(side="left", padx=4)

        self.btn_correct = tk.Button(btn_bar, text=self._t("correct"), width=10, command=lambda: self.answer(5), state=tk.DISABLED)
        self.btn_correct.pack(side="left", padx=4)

        self.btn_wrong = tk.Button(btn_bar, text=self._t("wrong"), width=10, command=lambda: self.answer(2), state=tk.DISABLED)
        self.btn_wrong.pack(side="left", padx=4)

        self.btn_restart = tk.Button(self, text=self._t("restart"), width=12, command=self.restart_session, state=tk.DISABLED)
        self.btn_restart.pack(pady=3)

        self.lbl_progress = tk.Label(self, text="")
        self.lbl_progress.pack()

        # ---------- Menu ----------
        menu = tk.Menu(self)
        file_menu = tk.Menu(menu, tearoff=0)
        file_menu.add_command(label=self._t("open"), command=self.open_file)
        file_menu.add_separator()
        file_menu.add_command(label=self._t("exit"), command=self.quit)
        menu.add_cascade(label=self._t("file"), menu=file_menu)

        lang_menu = tk.Menu(menu, tearoff=0)
        lang_menu.add_command(label=self._t("lang_ko"), command=lambda: self.set_lang("ko"))
        lang_menu.add_command(label=self._t("lang_en"), command=lambda: self.set_lang("en"))
        menu.add_cascade(label=self._t("menu_lang"), menu=lang_menu)

        self.config(menu=menu)

        # ---------- Hotkeys ----------
        self.bind("<space>", lambda _: self.toggle_answer())
        self.bind("<Right>", lambda _: self.next_card())
        self.bind("<Left>", lambda _: self.prev_card())
        self.bind("a", lambda _: self.answer(5))
        self.bind("s", lambda _: self.answer(2))
        self.bind("<F1>", lambda _: self.show_list())
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self._load_progress()

    # ---------------- i18n ----------------
    def _t(self, key):
        return LANG_DATA[self.lang][key]

    def set_lang(self, lang: str):
        if lang in LANG_DATA:
            self.lang = lang
            self._refresh_ui()

    def _refresh_ui(self):
        self.btn_prev.config(text=self._t("prev"))
        self.btn_show.config(text=self._t("show"))
        self.btn_next.config(text=self._t("next"))
        self.btn_correct.config(text=self._t("correct"))
        self.btn_wrong.config(text=self._t("wrong"))
        self.btn_restart.config(text=self._t("restart"))
        self.update_progress()
        if not self.cards:
            self.lbl_text.config(text=self._t("no_file"))

    # ---------------- File Handling ----------------
    def open_file(self):
        path = filedialog.askopenfilename(title=self._t("open"), filetypes=[("CSV","*.csv"),("All","*.*")])
        if not path:
            return
        try:
            self.cards = self._load_csv(Path(path))
            self.csv_path = Path(path)
        except Exception as e:
            messagebox.showerror(self._t("error_read"), str(e))
            return
        for w, _ in self.cards:
            self.stats.setdefault(w, CardStats())
        self.restart_session()

    def _load_csv(self, path: Path):
        out = []
        with path.open(newline='', encoding='utf-8') as f:
            for row in csv.reader(f):
                if len(row) < 2:      # 단어 칸조차 없으면 skip
                    continue
                word = row[0].strip()
                # 맨 끝 셀이 0/1 이면 결과, 아니면 결과 없음
                maybe_result = row[-1].strip()
                if maybe_result in ('0', '1'):
                    result = int(maybe_result)
                    meaning_cells = row[1:-1]
                else:
                    result = None
                    meaning_cells = row[1:]
                meaning = ', '.join(c.strip() for c in meaning_cells)
                out.append((word, meaning))
                if result is not None:
                    self.results[word] = result
        return out

    # ---------------- Session Deck ----------------
    def restart_session(self):
        today = dt.date.today()
        self.deck = [c for c in self.cards if self.stats[c[0]].next_due <= today]
        random.shuffle(self.deck)
        self.idx = -1
        self.btn_prev.config(state=tk.DISABLED)
        self.btn_show.config(state=tk.NORMAL)
        self.btn_next.config(state=tk.NORMAL)
        self.btn_restart.config(state=tk.DISABLED)
        self.next_card()

    def next_card(self):
        if not self.deck:
            return
        if self.idx >= len(self.deck) - 1:
            self.finish_deck()
            return
        self.idx += 1
        self.show_current()

    def prev_card(self):
        if self.idx > 0:
            self.idx -= 1
            self.show_current()

    def show_current(self):
        self.showing_answer = False
        w, _ = self.deck[self.idx]
        self.lbl_text.config(text=w)
        self.btn_correct.config(state=tk.DISABLED)
        self.btn_wrong.config(state=tk.DISABLED)
        self.btn_prev.config(state=tk.NORMAL if self.idx > 0 else tk.DISABLED)
        self.btn_next.config(state=tk.NORMAL)
        self.update_progress()

    def toggle_answer(self):
        if not self.deck or self.idx < 0:
            return
        self.showing_answer = not self.showing_answer
        word, meaning = self.deck[self.idx]
        if self.showing_answer:
            self.lbl_text.config(text=meaning)
            self.btn_correct.config(state=tk.NORMAL)
            self.btn_wrong.config(state=tk.NORMAL)
        else:
            self.lbl_text.config(text=word)
            self.btn_correct.config(state=tk.DISABLED)
            self.btn_wrong.config(state=tk.DISABLED)

    def answer(self, quality: int):
        if not self.deck or self.idx < 0 or not self.showing_answer:
            return
        word, _ = self.deck[self.idx]
        cs = self.stats[word]
        cs.ef, cs.interval, cs.reps = sm2_update(cs.ef, cs.interval, cs.reps, quality)
        cs.next_due = dt.date.today() + dt.timedelta(days=cs.interval)
        self.results[word] = 1 if quality >= 3 else 0
        # move to next automatically
        self.next_card()

    def finish_deck(self):
        self.lbl_text.config(text=self._t("finished"))
        self.btn_correct.config(state=tk.DISABLED)
        self.btn_wrong.config(state=tk.DISABLED)
        self.btn_prev.config(state=tk.NORMAL if self.idx >= 0 else tk.DISABLED)
        self.btn_next.config(state=tk.DISABLED)
        self.btn_show.config(state=tk.DISABLED)
        self.btn_restart.config(state=tk.NORMAL)
        self.update_progress()

    def update_progress(self):
        total = len(self.deck) if self.deck else 0
        done = self.idx + 1 if self.idx >= 0 else 0
        pct = done / total if total else 0
        self.lbl_progress.config(text=self._t("progress").format(done=done, total=total, pct=pct))

    # ---------------- List Popup (F1) ----------------
    def show_list(self):
        if not self.deck:
            return
        win = tk.Toplevel(self)
        win.title(self._t("list_title"))
        win.geometry("300x400")
        box = tk.Listbox(win, font=("Helvetica", 12))
        for w, m in self.deck:
            box.insert(tk.END, f"{w} → {m}")
        box.pack(fill=tk.BOTH, expand=True)

    # ---------------- Persistence ----------------
    def _load_progress(self):
        if not os.path.exists(PROG_FILE):
            return
        try:
            with open(PROG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.stats = {w: CardStats.from_json(val) for w, val in data.get("stats", {}).items()}
            self.results = {w: int(v) for w, v in data.get("results", {}).items()}
        except Exception:
            self.stats = {}
            self.results = {}

    def _save_progress(self):
        with open(PROG_FILE, "w", encoding="utf-8") as f:
            payload = {
                "stats": {w: s.to_json() for w, s in self.stats.items()},
                "results": self.results,
            }
            json.dump(payload, f, ensure_ascii=False, indent=2)
        # also update CSV 3rd column
        if self.csv_path and self.cards:
            tmp = self.csv_path.with_suffix(".tmp")
            with self.csv_path.open(newline="", encoding="utf-8") as fr, tmp.open("w", newline="", encoding="utf-8") as fw:
                reader = list(csv.reader(fr))
                writer = csv.writer(fw)
                for row in reader:
                    if len(row) < 2:
                        continue
                    word = row[0].strip()
                    result = self.results.get(word)
                    if result is not None:
                        if len(row) >= 3:
                            row[2] = str(result)
                        else:
                            row.append(str(result))
                    writer.writerow(row)
            tmp.replace(self.csv_path)

    # ---------------- Window close ----------------
    def on_close(self):
        self._save_progress()
        self.destroy()

if __name__ == "__main__":
    FlashcardApp().mainloop()