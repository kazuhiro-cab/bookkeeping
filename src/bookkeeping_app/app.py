from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from .models import (
    AcceptableAnswer,
    AnswerStatus,
    CopyrightType,
    LedgerEffectTemplate,
    LearningMode,
    Question,
    QuestionStatus,
    ScoringRule,
)
from .service import BookkeepingService


class BookkeepingApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("会計処理練習ツール")
        self.root.geometry("980x680")

        self.service = BookkeepingService()
        self.current_user_id: str | None = None
        self.current_session_id: str | None = None
        self.current_question_id: str | None = None

        self._build_ui()
        self._seed_sample_question()

    def _build_ui(self) -> None:
        frame = ttk.Frame(self.root, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        profile = ttk.LabelFrame(frame, text="学習者/モード", padding=8)
        profile.pack(fill=tk.X)

        ttk.Label(profile, text="学習者名").grid(row=0, column=0, sticky=tk.W)
        self.user_name_var = tk.StringVar(value="学習者")
        ttk.Entry(profile, textvariable=self.user_name_var, width=24).grid(row=0, column=1, sticky=tk.W, padx=4)

        ttk.Label(profile, text="学習モード").grid(row=0, column=2, sticky=tk.W, padx=(12, 0))
        self.mode_var = tk.StringVar(value=LearningMode.DOUBLE_ENTRY.value)
        self.mode_combo = ttk.Combobox(
            profile,
            textvariable=self.mode_var,
            values=[m.value for m in LearningMode],
            width=28,
            state="readonly",
        )
        self.mode_combo.grid(row=0, column=3, sticky=tk.W, padx=4)

        ttk.Button(profile, text="学習者作成/切替", command=self.create_or_switch_user).grid(row=0, column=4, padx=8)
        ttk.Button(profile, text="セッション開始", command=self.start_session).grid(row=0, column=5, padx=4)

        question_frame = ttk.LabelFrame(frame, text="出題", padding=8)
        question_frame.pack(fill=tk.X, pady=(10, 0))
        self.question_title = tk.StringVar(value="未出題")
        self.question_body = tk.StringVar(value="セッション開始後に問題を出題します。")
        ttk.Label(question_frame, textvariable=self.question_title, font=("Meiryo UI", 11, "bold")).pack(anchor=tk.W)
        ttk.Label(question_frame, textvariable=self.question_body, wraplength=920).pack(anchor=tk.W, pady=(4, 0))
        ttk.Button(question_frame, text="問題を出題", command=self.issue_question).pack(anchor=tk.W, pady=(8, 0))

        answer = ttk.LabelFrame(frame, text="回答/採点", padding=8)
        answer.pack(fill=tk.X, pady=(10, 0))
        ttk.Label(answer, text="借方").grid(row=0, column=0, sticky=tk.W)
        self.debit_var = tk.StringVar()
        ttk.Entry(answer, textvariable=self.debit_var, width=22).grid(row=0, column=1, padx=4)

        ttk.Label(answer, text="貸方").grid(row=0, column=2, sticky=tk.W, padx=(10, 0))
        self.credit_var = tk.StringVar()
        ttk.Entry(answer, textvariable=self.credit_var, width=22).grid(row=0, column=3, padx=4)

        ttk.Button(answer, text="一時保存", command=lambda: self.save_answer(AnswerStatus.TEMPORARY_SAVED)).grid(row=0, column=4, padx=6)
        ttk.Button(answer, text="回答確定", command=lambda: self.save_answer(AnswerStatus.SUBMITTED)).grid(row=0, column=5, padx=6)
        ttk.Button(answer, text="採点", command=self.score_latest_submission).grid(row=0, column=6, padx=6)

        result_frame = ttk.LabelFrame(frame, text="結果/解説/帳簿影響", padding=8)
        result_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        self.result_text = tk.Text(result_frame, height=18)
        self.result_text.pack(fill=tk.BOTH, expand=True)

    def _seed_sample_question(self) -> None:
        q = Question(
            title="商品売上（掛け）",
            body="商品を掛けで販売した。適切な仕訳を入力してください。",
            mode=LearningMode.DOUBLE_ENTRY,
            topic_id="sales",
            question_type="複式簿記",
            question_status=QuestionStatus.PUBLISHABLE,
            copyright_type=CopyrightType.ORIGINAL,
            owner_user_id=None,
        )
        self.service.create_question(q, changed_by="system")
        self.service.add_acceptable_answer(
            AcceptableAnswer(
                question_id=q.id,
                scoring_mode="strict",
                answer_data={"debit": "売掛金", "credit": "売上"},
            )
        )
        self.service.add_scoring_rule(
            ScoringRule(
                question_id=q.id,
                scoring_rule_data={"elements": [{"key": "debit", "points": 50}, {"key": "credit", "points": 50}]},
            )
        )
        self.service.set_ledger_effect(
            LedgerEffectTemplate(
                question_id=q.id,
                effect_data={
                    "journal": ["借方: 売掛金 / 貸方: 売上"],
                    "general_ledger": ["売掛金元帳に増加", "売上元帳に増加"],
                    "trial_balance": ["資産増加", "収益増加"],
                    "financial_statements": ["PL売上高+", "BS売掛金+"],
                    "cost_reports": [],
                },
            )
        )
        self.current_question_id = q.id

    def create_or_switch_user(self) -> None:
        name = self.user_name_var.get().strip()
        if not name:
            messagebox.showerror("入力エラー", "学習者名を入力してください。")
            return

        if self.current_user_id is None:
            user = self.service.create_user(name)
            self.current_user_id = user.id
        mode = LearningMode(self.mode_var.get())
        self.service.switch_learning_mode(self.current_user_id, mode)
        self._append_result(f"学習者設定: {name} / モード: {mode.value}")

    def start_session(self) -> None:
        if self.current_user_id is None:
            self.create_or_switch_user()
            if self.current_user_id is None:
                return
        session = self.service.start_session(self.current_user_id, LearningMode(self.mode_var.get()))
        self.current_session_id = session.id
        self._append_result(f"セッション開始: {session.id}")

    def issue_question(self) -> None:
        if self.current_session_id is None:
            messagebox.showerror("セッション未開始", "先にセッションを開始してください。")
            return
        if self.current_question_id is None:
            return
        self.service.issue_questions(self.current_session_id, [self.current_question_id])
        q = self.service.questions[self.current_question_id]
        self.question_title.set(q.title)
        self.question_body.set(q.body)
        self._append_result(f"出題: {q.title}")

    def save_answer(self, status: AnswerStatus) -> None:
        if self.current_session_id is None or self.current_question_id is None:
            messagebox.showerror("未開始", "先にセッション開始と出題を行ってください。")
            return
        answer = self.service.save_answer(
            self.current_session_id,
            self.current_question_id,
            {"debit": self.debit_var.get().strip(), "credit": self.credit_var.get().strip()},
            status,
        )
        self._append_result(f"回答保存: {status.value} / answer_id={answer.id}")

    def score_latest_submission(self) -> None:
        submitted = [a for a in self.service.answers if a.answer_status == AnswerStatus.SUBMITTED]
        if not submitted:
            messagebox.showerror("採点不可", "先に回答確定を行ってください。")
            return
        result = self.service.score_answer(submitted[-1].id, scoring_mode="strict")
        ledger = self.service.get_ledger_impact(result.question_id)
        self._append_result(
            "\n".join(
                [
                    f"採点結果: {result.points}点 ({result.result_status.value})",
                    f"採点根拠: {result.basis}",
                    f"要素別: {[f'{d.element}:{d.awarded_points}/{d.max_points}' for d in result.details]}",
                    f"仕訳帳影響: {ledger['journal']}",
                    f"総勘定元帳影響: {ledger['general_ledger']}",
                    f"試算表影響: {ledger['trial_balance']}",
                    f"財務諸表影響: {ledger['financial_statements']}",
                ]
            )
        )

    def _append_result(self, message: str) -> None:
        self.result_text.insert(tk.END, message + "\n")
        self.result_text.see(tk.END)


def main() -> None:
    root = tk.Tk()
    BookkeepingApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
