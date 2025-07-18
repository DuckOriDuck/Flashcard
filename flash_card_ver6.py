#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
플래시카드 학습 앱
- Python 3.10+ 및 Tkinter 사용
- UTF-8 인코딩 .txt 파일 지원
- 단어\뜻\결과 형식 (백슬래시 구분자)
- 키보드 단축키 지원 (Space, 방향키, A, S)
- 셔플 기능 토글 및 진행률 표시
- 정답/오답 실시간 저장
"""

import tkinter as tk
from tkinter import messagebox, filedialog, Menu
import random
import os
from pathlib import Path
from typing import List, Dict, Optional


class FlashcardApp:
    def __init__(self, root):
        self.root = root
        self.root.title("플래시카드 학습 앱")
        self.root.geometry("600x400")
        self.root.configure(bg='#f0f0f0')
        
        # 데이터 관련 변수
        self.cards: List[Dict] = []  # [{'word': str, 'meaning': str, 'result': str}, ...]
        self.original_cards: List[Dict] = []  # 원본 순서 저장
        self.current_index = 0
        self.show_answer = False
        self.file_path: Optional[str] = None
        self.reverse_mode = False  # False: 단어→정답, True: 정답→단어
        self.shuffle_enabled = False  # 셔플 활성화 여부
        
        # UI 설정
        self.setup_menu()
        self.setup_ui()
        self.setup_bindings()
        
    def setup_menu(self):
        """메뉴바 설정"""
        menubar = Menu(self.root)
        self.root.config(menu=menubar)
        
        # 파일 메뉴
        file_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="파일", menu=file_menu)
        file_menu.add_command(label="열기(txt)...", command=self.open_file, accelerator="Ctrl+O")
        file_menu.add_separator()
        file_menu.add_command(label="종료", command=self.root.quit)
        
        # 학습 메뉴
        study_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="학습", menu=study_menu)
        study_menu.add_command(label="재시작", command=self.restart_study, accelerator="Ctrl+R")
        study_menu.add_separator()
        study_menu.add_command(label="방향 전환", command=self.toggle_direction, accelerator="Ctrl+T")
        study_menu.add_command(label="셔플 토글", command=self.toggle_shuffle, accelerator="Ctrl+S")
        study_menu.add_separator()
        study_menu.add_command(label="카드 목록", command=self.show_card_list, accelerator="Ctrl+L")
        
    def setup_ui(self):
        """UI 구성 요소 설정"""
        # 상단 진행률 라벨
        self.progress_label = tk.Label(
            self.root, 
            text="파일을 열어주세요",
            font=("맑은 고딕", 12),
            bg='#f0f0f0',
            fg='#333333'
        )
        self.progress_label.pack(pady=10)
        
        # 상태 표시 프레임
        status_frame = tk.Frame(self.root, bg='#f0f0f0')
        status_frame.pack()
        
        # 방향 표시 라벨
        self.direction_label = tk.Label(
            status_frame,
            text="",
            font=("맑은 고딕", 10),
            bg='#f0f0f0',
            fg='#666666'
        )
        self.direction_label.pack(side='left', padx=5)
        
        # 셔플 상태 표시 라벨
        self.shuffle_label = tk.Label(
            status_frame,
            text="셔플: OFF",
            font=("맑은 고딕", 10),
            bg='#f0f0f0',
            fg='#666666'
        )
        self.shuffle_label.pack(side='left', padx=5)
        
        # 카드 표시 영역
        self.card_frame = tk.Frame(self.root, bg='white', relief='raised', bd=2)
        self.card_frame.pack(pady=20, padx=20, fill='both', expand=True)
        
        # 카드 내용 라벨
        self.card_label = tk.Label(
            self.card_frame,
            text="파일을 열어 학습을 시작하세요",
            font=("맑은 고딕", 16),
            bg='white',
            fg='#333333',
            wraplength=500,
            justify='center'
        )
        self.card_label.pack(expand=True)
        
        # 버튼 프레임
        button_frame = tk.Frame(self.root, bg='#f0f0f0')
        button_frame.pack(pady=10)
        
        # 이전 버튼
        self.prev_btn = tk.Button(
            button_frame,
            text="← 이전",
            command=self.prev_card,
            font=("맑은 고딕", 10),
            state='disabled'
        )
        self.prev_btn.pack(side='left', padx=5)
        
        # 답안 토글 버튼
        self.toggle_btn = tk.Button(
            button_frame,
            text="답안 보기 (Space)",
            command=self.toggle_answer,
            font=("맑은 고딕", 10),
            state='disabled'
        )
        self.toggle_btn.pack(side='left', padx=5)
        
        # 다음 버튼
        self.next_btn = tk.Button(
            button_frame,
            text="다음 →",
            command=self.next_card,
            font=("맑은 고딕", 10),
            state='disabled'
        )
        self.next_btn.pack(side='left', padx=5)
        
        # 정답/오답 버튼
        result_frame = tk.Frame(self.root, bg='#f0f0f0')
        result_frame.pack(pady=5)
        
        self.correct_btn = tk.Button(
            result_frame,
            text="정답 (A)",
            command=self.mark_correct,
            font=("맑은 고딕", 10),
            bg='#4CAF50',
            fg='white',
            state='disabled'
        )
        self.correct_btn.pack(side='left', padx=5)
        
        self.wrong_btn = tk.Button(
            result_frame,
            text="오답 (S)",
            command=self.mark_wrong,
            font=("맑은 고딕", 10),
            bg='#f44336',
            fg='white',
            state='disabled'
        )
        self.wrong_btn.pack(side='left', padx=5)
        
        # 재시작 버튼
        self.restart_btn = tk.Button(
            result_frame,
            text="재시작",
            command=self.restart_study,
            font=("맑은 고딕", 10),
            state='disabled'
        )
        self.restart_btn.pack(side='left', padx=5)
        
        # 방향 전환 버튼
        self.toggle_direction_btn = tk.Button(
            result_frame,
            text="방향 전환",
            command=self.toggle_direction,
            font=("맑은 고딕", 10),
            state='disabled'
        )
        self.toggle_direction_btn.pack(side='left', padx=5)
        
        # 셔플 토글 버튼
        self.shuffle_btn = tk.Button(
            result_frame,
            text="셔플 ON",
            command=self.toggle_shuffle,
            font=("맑은 고딕", 10),
            bg='#2196F3',
            fg='white',
            state='disabled'
        )
        self.shuffle_btn.pack(side='left', padx=5)
        
        # 도움말 라벨
        help_label = tk.Label(
            self.root,
            text="단축키: Space(답안토글), ←→(이전/다음), A(정답), S(오답), Ctrl+T(방향전환), Ctrl+S(셔플토글)",
            font=("맑은 고딕", 9),
            bg='#f0f0f0',
            fg='#666666'
        )
        help_label.pack(pady=5)
        
    def setup_bindings(self):
        """키보드 단축키 바인딩"""
        self.root.bind('<space>', lambda e: self.toggle_answer())
        self.root.bind('<Left>', lambda e: self.prev_card())
        self.root.bind('<Right>', lambda e: self.next_card())
        self.root.bind('<a>', lambda e: self.mark_correct())
        self.root.bind('<A>', lambda e: self.mark_correct())
        self.root.bind('<s>', lambda e: self.mark_wrong())
        self.root.bind('<S>', lambda e: self.mark_wrong())
        self.root.bind('<Control-o>', lambda e: self.open_file())
        self.root.bind('<Control-r>', lambda e: self.restart_study())
        self.root.bind('<Control-l>', lambda e: self.show_card_list())
        self.root.bind('<Control-t>', lambda e: self.toggle_direction())
        self.root.bind('<Control-s>', lambda e: self.toggle_shuffle())
        
        # 포커스 설정 (키보드 이벤트 수신용)
        self.root.focus_set()
        
    def open_file(self):
        """파일 열기"""
        file_path = filedialog.askopenfilename(
            title="플래시카드 파일 선택",
            filetypes=[("텍스트 파일", "*.txt"), ("모든 파일", "*.*")]
        )
        
        if file_path:
            try:
                self.load_cards(file_path)
                self.file_path = file_path
                self.restart_study()
                messagebox.showinfo("성공", f"파일을 성공적으로 열었습니다!\n총 {len(self.cards)}개의 카드가 로드되었습니다.")
            except Exception as e:
                messagebox.showerror("오류", f"파일을 열 수 없습니다:\n{str(e)}")
                
    def load_cards(self, file_path: str):
        """파일에서 카드 데이터 로드"""
        cards = []
        
        with open(file_path, 'r', encoding='utf-8') as file:
            for line_num, line in enumerate(file, 1):
                line = line.strip()
                if not line:
                    continue
                    
                parts = line.split('\\')
                if len(parts) < 2:
                    continue
                    
                word = parts[0].strip()
                meaning = parts[1].strip()
                result = parts[2].strip() if len(parts) > 2 else ''
                
                cards.append({
                    'word': word,
                    'meaning': meaning,
                    'result': result
                })
        
        if not cards:
            raise ValueError("유효한 카드를 찾을 수 없습니다.")
        
        # 원본 순서 저장
        self.original_cards = cards.copy()
        self.cards = cards
        
    def restart_study(self):
        """학습 재시작 (셔플 설정에 따라)"""
        if not self.cards:
            messagebox.showwarning("경고", "먼저 파일을 열어주세요.")
            return
        
        # 셔플 설정에 따라 카드 순서 결정
        if self.shuffle_enabled:
            self.cards = self.original_cards.copy()
            random.shuffle(self.cards)
        else:
            self.cards = self.original_cards.copy()
        
        # 초기 상태 설정
        self.current_index = 0
        self.show_answer = False
        
        # UI 업데이트
        self.update_display()
        self.enable_buttons()
        
    def toggle_shuffle(self):
        """셔플 기능 토글"""
        if not self.cards:
            messagebox.showwarning("경고", "먼저 파일을 열어주세요.")
            return
        
        self.shuffle_enabled = not self.shuffle_enabled
        
        # 버튼 및 라벨 업데이트
        if self.shuffle_enabled:
            self.shuffle_btn.config(text="셔플 OFF", bg='#ff9800')
            self.shuffle_label.config(text="셔플: ON", fg='#ff9800')
        else:
            self.shuffle_btn.config(text="셔플 ON", bg='#2196F3')
            self.shuffle_label.config(text="셔플: OFF", fg='#666666')
        
        # 즉시 재시작하여 설정 적용
        self.restart_study()
        
        status_text = "활성화" if self.shuffle_enabled else "비활성화"
        messagebox.showinfo("셔플 토글", f"셔플 기능이 {status_text}되었습니다.\n카드 순서가 재설정되었습니다.")
        
    def update_display(self):
        """현재 카드 표시 업데이트"""
        if not self.cards:
            return
            
        current_card = self.cards[self.current_index]
        
        # 방향에 따라 질문과 답안 결정
        if self.reverse_mode:
            question = current_card['meaning']
            answer = current_card['word']
        else:
            question = current_card['word']
            answer = current_card['meaning']
        
        # 진행률 업데이트
        self.progress_label.config(text=f"{self.current_index + 1}/{len(self.cards)}")
        
        # 방향 표시 업데이트
        direction_text = "정답 → 단어" if self.reverse_mode else "단어 → 정답"
        self.direction_label.config(text=f"학습 방향: {direction_text}")
        
        # 카드 내용 업데이트
        if self.show_answer:
            display_text = f"Q: {question}\n\nA: {answer}"
            self.card_label.config(text=display_text, fg='#0066cc')
            self.toggle_btn.config(text="질문 보기 (Space)")
        else:
            display_text = f"Q: {question}\n\n(Space를 눌러 답안 확인)"
            self.card_label.config(text=display_text, fg='#333333')
            self.toggle_btn.config(text="답안 보기 (Space)")
            
        # 결과 표시 (카드 배경색으로)
        result = current_card['result']
        if result == '1':
            self.card_frame.config(bg='#e8f5e8')
        elif result == '0':
            self.card_frame.config(bg='#ffeaea')
        else:
            self.card_frame.config(bg='white')
            
    def toggle_answer(self):
        """답안 토글"""
        if not self.cards:
            return
            
        self.show_answer = not self.show_answer
        self.update_display()
        
    def prev_card(self):
        """이전 카드"""
        if not self.cards:
            return
            
        if self.current_index > 0:
            self.current_index -= 1
            self.show_answer = False
            self.update_display()
            
    def next_card(self):
        """다음 카드"""
        if not self.cards:
            return
            
        if self.current_index < len(self.cards) - 1:
            self.current_index += 1
            self.show_answer = False
            self.update_display()
        else:
            messagebox.showinfo("완료", "모든 카드를 학습했습니다!")
            
    def mark_correct(self):
        """정답 처리"""
        if not self.cards:
            return
            
        self.cards[self.current_index]['result'] = '1'
        self.save_results()
        self.update_display()
        
    def mark_wrong(self):
        """오답 처리"""
        if not self.cards:
            return
            
        self.cards[self.current_index]['result'] = '0'
        self.save_results()
        self.update_display()
        
    def toggle_direction(self):
        """학습 방향 전환 (단어→정답 ↔ 정답→단어)"""
        if not self.cards:
            messagebox.showwarning("경고", "먼저 파일을 열어주세요.")
            return
            
        self.reverse_mode = not self.reverse_mode
        self.show_answer = False  # 답안 숨기기
        self.update_display()
        
        direction_text = "정답 → 단어" if self.reverse_mode else "단어 → 정답"
        messagebox.showinfo("방향 전환", f"학습 방향이 '{direction_text}'로 변경되었습니다.")
    
    def save_results(self):
        """결과를 파일에 저장"""
        if not self.file_path:
            return
            
        try:
            # 백업 파일 생성
            backup_path = self.file_path + '.backup'
            if os.path.exists(self.file_path):
                import shutil
                shutil.copy2(self.file_path, backup_path)
            
            # 원본 순서로 저장하기 위해 original_cards 사용
            # 현재 카드의 결과를 original_cards에 반영
            current_card = self.cards[self.current_index]
            for orig_card in self.original_cards:
                if orig_card['word'] == current_card['word'] and orig_card['meaning'] == current_card['meaning']:
                    orig_card['result'] = current_card['result']
                    break
            
            # 새 내용으로 파일 쓰기
            with open(self.file_path, 'w', encoding='utf-8') as file:
                for card in self.original_cards:
                    line = f"{card['word']}\\{card['meaning']}\\{card['result']}\n"
                    file.write(line)
                    
        except Exception as e:
            messagebox.showerror("저장 오류", f"결과를 저장하는 중 오류가 발생했습니다:\n{str(e)}")
            
    def show_card_list(self):
        """카드 목록 팝업"""
        if not self.cards:
            messagebox.showwarning("경고", "먼저 파일을 열어주세요.")
            return
            
        # 새 창 생성
        list_window = tk.Toplevel(self.root)
        list_window.title("카드 목록")
        list_window.geometry("500x400")
        list_window.configure(bg='#f0f0f0')
        
        # 스크롤 가능한 텍스트 영역
        from tkinter import scrolledtext
        
        text_area = scrolledtext.ScrolledText(
            list_window,
            wrap=tk.WORD,
            width=60,
            height=20,
            font=("맑은 고딕", 10)
        )
        text_area.pack(fill='both', expand=True, padx=10, pady=10)
        
        # 카드 목록 표시
        for i, card in enumerate(self.cards, 1):
            result_text = ""
            if card['result'] == '1':
                result_text = " ✓"
            elif card['result'] == '0':
                result_text = " ✗"
                
            text_area.insert(tk.END, f"{i}. {card['word']}{result_text}\n")
            text_area.insert(tk.END, f"   → {card['meaning']}\n\n")
            
        text_area.config(state='disabled')
        
    def enable_buttons(self):
        """버튼 활성화"""
        self.toggle_btn.config(state='normal')
        self.next_btn.config(state='normal')
        self.prev_btn.config(state='normal')
        self.correct_btn.config(state='normal')
        self.wrong_btn.config(state='normal')
        self.restart_btn.config(state='normal')
        self.toggle_direction_btn.config(state='normal')
        self.shuffle_btn.config(state='normal')


def main():
    """메인 함수"""
    root = tk.Tk()
    app = FlashcardApp(root)
    
    # 창 아이콘 설정 (선택사항)
    try:
        root.iconbitmap(default='flashcard.ico')
    except:
        pass  # 아이콘 파일이 없어도 무시
    
    # 창 종료 처리
    def on_closing():
        root.quit()
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    
    # 앱 실행
    root.mainloop()


if __name__ == "__main__":
    main()