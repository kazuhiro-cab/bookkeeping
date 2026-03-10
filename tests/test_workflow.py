import io
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

import unittest

from bookkeeping_app.models import (
    AcceptableAnswer,
    AnswerStatus,
    CopyrightType,
    ExplanationView,
    LedgerEffectTemplate,
    LearningMode,
    Question,
    QuestionStatus,
    ScoringRule,
)
from bookkeeping_app.service import BookkeepingService


class WorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = BookkeepingService()
        self.user = self.service.create_user("learner")
        self.service.switch_learning_mode(self.user.id, LearningMode.DOUBLE_ENTRY)

        self.question = Question(
            title="商品売上",
            body="掛け売上",
            mode=LearningMode.DOUBLE_ENTRY,
            topic_id="sales",
            question_type="複式簿記",
            question_status=QuestionStatus.PUBLISHABLE,
            copyright_type=CopyrightType.LICENSED,
            owner_user_id=None,
        )
        self.service.create_question(self.question, changed_by="admin")
        self.service.add_acceptable_answer(
            AcceptableAnswer(
                question_id=self.question.id,
                scoring_mode="strict",
                answer_data={"debit": "売掛金", "credit": "売上"},
            )
        )
        self.service.add_scoring_rule(
            ScoringRule(
                question_id=self.question.id,
                scoring_rule_data={"elements": [{"key": "debit", "points": 50}, {"key": "credit", "points": 50}]},
            )
        )
        self.service.add_explanation(
            ExplanationView(
                question_id=self.question.id,
                level="標準",
                explanation="売上は収益",
                common_mistakes=["現金売上と誤認"],
                fs_impact="PLの売上増加、BSの売掛金増加",
                cost_impact="該当なし",
            )
        )
        self.service.set_ledger_effect(
            LedgerEffectTemplate(
                question_id=self.question.id,
                effect_data={
                    "journal": ["借方:売掛金 / 貸方:売上"],
                    "general_ledger": ["売掛金元帳", "売上元帳"],
                    "trial_balance": ["売掛金+", "売上+"],
                    "financial_statements": ["PL", "BS"],
                    "cost_reports": [],
                },
            )
        )

    def test_session_issue_save_submit_score_and_history(self):
        session = self.service.start_session(self.user.id, LearningMode.DOUBLE_ENTRY)
        self.service.issue_questions(session.id, [self.question.id])
        tmp = self.service.save_answer(
            session.id, self.question.id, {"debit": "売掛金", "credit": "仮受金"}, AnswerStatus.TEMPORARY_SAVED
        )
        submitted = self.service.save_answer(
            session.id, self.question.id, {"debit": "売掛金", "credit": "売上"}, AnswerStatus.SUBMITTED
        )
        result = self.service.score_answer(submitted.id, scoring_mode="strict")
        self.assertEqual(result.points, 100)
        self.assertEqual(len(result.details), 2)
        self.assertNotEqual(tmp.id, submitted.id)

        self.service.complete_session(session.id)
        history = self.service.get_history(self.user.id)
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0].status.value, "completed")

    def test_tax_precondition_is_required(self):
        q = Question(
            title="消費税仮払",
            body="税金仕訳",
            mode=LearningMode.TAX_JOURNAL,
            topic_id="tax",
            question_type="税金仕訳",
            question_status=QuestionStatus.PUBLISHABLE,
            copyright_type=CopyrightType.ORIGINAL,
            owner_user_id=None,
        )
        self.service.create_question(q, changed_by="admin")
        self.service.add_acceptable_answer(
            AcceptableAnswer(
                question_id=q.id,
                scoring_mode="strict",
                answer_data={"debit": "仮払消費税", "credit": "現金"},
                precondition="課税事業者",
                precondition_version="2024",
            )
        )
        self.service.add_scoring_rule(
            ScoringRule(
                question_id=q.id,
                scoring_rule_data={"elements": [{"key": "debit", "points": 50}, {"key": "credit", "points": 50}]},
            )
        )
        session = self.service.start_session(self.user.id, LearningMode.TAX_JOURNAL)
        self.service.issue_questions(session.id, [q.id])
        ans = self.service.save_answer(
            session.id, q.id, {"debit": "仮払消費税", "credit": "現金"}, AnswerStatus.SUBMITTED
        )
        unscored = self.service.score_answer(ans.id, scoring_mode="strict")
        self.assertEqual(unscored.result_status.value, "unscored")
        scored = self.service.score_answer(
            ans.id, scoring_mode="strict", tax_precondition="課税事業者", tax_precondition_version="2024"
        )
        self.assertEqual(scored.result_status.value, "correct")

    def test_copyright_and_publish_control(self):
        blocked = Question(
            title="blocked",
            body="...",
            mode=LearningMode.SINGLE_ENTRY,
            topic_id="cashbook",
            question_type="単式簿記",
            question_status=QuestionStatus.PUBLISHABLE,
            copyright_type=CopyrightType.UNCONFIRMED,
            owner_user_id=None,
        )
        with self.assertRaises(ValueError):
            self.service.create_question(blocked, changed_by="admin")

    def test_explanation_ledger_weakpoint_export_csv_import(self):
        session = self.service.start_session(self.user.id, LearningMode.DOUBLE_ENTRY)
        self.service.issue_questions(session.id, [self.question.id])
        ans = self.service.save_answer(
            session.id, self.question.id, {"debit": "現金", "credit": "売上"}, AnswerStatus.SUBMITTED
        )
        self.service.score_answer(ans.id, scoring_mode="strict")

        explanations = self.service.get_explanations(self.question.id)
        self.assertEqual(explanations[0].level, "標準")
        ledger = self.service.get_ledger_impact(self.question.id)
        self.assertIn("trial_balance", ledger)

        weak_points = self.service.summarize_weak_points(self.user.id)
        self.assertEqual(weak_points[0].topic_id, "sales")

        exported = self.service.export_user_results_csv(self.user.id)
        self.assertIn("result_status", exported)

        csv_data = "title,body,mode,topic_id,question_type,question_status,copyright_type,owner_user_id,source_text,reconstructed_text\n"
        csv_data += "CSV問題,本文,複式簿記モード,sales,複式簿記,publishable,独自作成,,,\n"
        csv_data += "NG問題,本文,複式簿記モード,sales,複式簿記,publishable,利用条件未確認,,,\n"
        batch = self.service.import_questions_csv(csv_data, changed_by="admin")
        self.assertEqual(batch.success_rows, 1)
        self.assertEqual(batch.failed_rows, 1)

    def test_pdf_import_and_auto_download(self):
        with patch.object(self.service, "_extract_text_by_page", return_value=["第1問 仕訳", "第2問 仕訳"]):
            batch = self.service.import_questions_pdf(
                b"%PDF-1.4 mock",
                changed_by="admin",
                mode=LearningMode.DOUBLE_ENTRY,
                topic_id="past_exam",
                question_type="総合問題",
                copyright_type=CopyrightType.LICENSED,
                question_status=QuestionStatus.PENDING_REVIEW,
                title_prefix="日商簿記過去問",
                source_text="manual-pdf",
            )
        self.assertEqual(batch.success_rows, 2)
        created = [q for q in self.service.questions.values() if q.topic_id == "past_exam"]
        self.assertEqual(len(created), 2)

        fake_response = MagicMock()
        fake_response.__enter__.return_value = fake_response
        fake_response.__exit__.return_value = None
        fake_response.headers = {"Content-Type": "application/pdf"}
        fake_response.read.return_value = b"%PDF-1.4 downloaded"

        with patch("bookkeeping_app.service.urllib.request.urlopen", return_value=fake_response):
            with patch.object(self.service, "_extract_text_by_page", return_value=["自動DL過去問"]):
                auto_batch = self.service.import_questions_pdf_from_url(
                    "https://example.com/kakomon.pdf",
                    changed_by="admin",
                    mode=LearningMode.DOUBLE_ENTRY,
                    topic_id="past_exam_auto",
                    question_type="総合問題",
                    copyright_type=CopyrightType.LICENSED,
                    question_status=QuestionStatus.PENDING_REVIEW,
                    title_prefix="自動DL",
                )

        self.assertEqual(auto_batch.success_rows, 1)


if __name__ == "__main__":
    unittest.main()
