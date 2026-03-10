from __future__ import annotations

import csv
import io
from collections import defaultdict
from dataclasses import asdict
from datetime import datetime
from typing import Dict, List, Optional

from .models import (
    AcceptableAnswer,
    Answer,
    AnswerStatus,
    CopyrightType,
    ExplanationView,
    ImportBatch,
    ImportError,
    LedgerEffectTemplate,
    LearningMode,
    LearningSession,
    LearningSessionStatus,
    Question,
    QuestionRevision,
    QuestionStatus,
    ResultStatus,
    ScoreResult,
    ScoreResultDetail,
    ScoringRule,
    SessionQuestion,
    StudyProfile,
    User,
    WeakPointSummary,
)


class BookkeepingService:
    def __init__(self) -> None:
        self.users: Dict[str, User] = {}
        self.study_profiles: Dict[str, StudyProfile] = {}
        self.learning_sessions: Dict[str, LearningSession] = {}
        self.questions: Dict[str, Question] = {}
        self.question_revisions: List[QuestionRevision] = []
        self.acceptable_answers: Dict[str, List[AcceptableAnswer]] = defaultdict(list)
        self.scoring_rules: Dict[str, ScoringRule] = {}
        self.session_questions: List[SessionQuestion] = []
        self.answers: List[Answer] = []
        self.score_results: List[ScoreResult] = []
        self.explanations: Dict[str, List[ExplanationView]] = defaultdict(list)
        self.ledger_effects: Dict[str, LedgerEffectTemplate] = {}
        self.import_batches: List[ImportBatch] = []
        self.import_errors: List[ImportError] = []

    def create_user(self, name: str) -> User:
        user = User(name=name)
        self.users[user.id] = user
        return user

    def switch_learning_mode(self, user_id: str, mode: LearningMode) -> StudyProfile:
        profile = next((p for p in self.study_profiles.values() if p.user_id == user_id), None)
        if profile is None:
            profile = StudyProfile(user_id=user_id, active_mode=mode)
            self.study_profiles[profile.id] = profile
        else:
            profile.active_mode = mode
        return profile

    def create_question(self, question: Question, changed_by: str) -> Question:
        if question.copyright_type == CopyrightType.UNCONFIRMED:
            raise ValueError("著作権区分が未確認の教材は登録不可です。")
        self.questions[question.id] = question
        self.question_revisions.append(
            QuestionRevision(
                question_id=question.id,
                changed_by=changed_by,
                reason="create",
                before={},
                after=asdict(question),
            )
        )
        return question

    def update_question_status(self, question_id: str, new_status: QuestionStatus, changed_by: str, reason: str) -> None:
        before = asdict(self.questions[question_id])
        self.questions[question_id].question_status = new_status
        after = asdict(self.questions[question_id])
        self.question_revisions.append(
            QuestionRevision(question_id=question_id, changed_by=changed_by, reason=reason, before=before, after=after)
        )

    def add_acceptable_answer(self, answer: AcceptableAnswer) -> AcceptableAnswer:
        self.acceptable_answers[answer.question_id].append(answer)
        return answer

    def add_scoring_rule(self, rule: ScoringRule) -> ScoringRule:
        self.scoring_rules[rule.question_id] = rule
        return rule

    def add_explanation(self, explanation: ExplanationView) -> None:
        self.explanations[explanation.question_id].append(explanation)

    def set_ledger_effect(self, effect: LedgerEffectTemplate) -> None:
        self.ledger_effects[effect.question_id] = effect

    def start_session(self, user_id: str, mode: LearningMode) -> LearningSession:
        session = LearningSession(user_id=user_id, mode=mode)
        self.learning_sessions[session.id] = session
        return session

    def issue_questions(self, session_id: str, question_ids: List[str]) -> List[SessionQuestion]:
        issued: List[SessionQuestion] = []
        for seq, qid in enumerate(question_ids, start=1):
            q = self.questions[qid]
            if q.question_status != QuestionStatus.PUBLISHABLE:
                raise ValueError("publishable 状態以外は出題不可です。")
            if q.copyright_type in (CopyrightType.UNCONFIRMED, CopyrightType.PROHIBITED):
                raise ValueError("著作権条件を満たさない教材は出題不可です。")
            issued_q = SessionQuestion(session_id=session_id, question_id=qid, sequence_no=seq)
            self.session_questions.append(issued_q)
            issued.append(issued_q)
        return issued

    def save_answer(self, session_id: str, question_id: str, answer_data: Dict, status: AnswerStatus) -> Answer:
        answer = Answer(session_id=session_id, question_id=question_id, answer_data=answer_data, answer_status=status)
        self.answers.append(answer)
        return answer

    def score_answer(
        self,
        answer_id: str,
        scoring_mode: str,
        tax_precondition: Optional[str] = None,
        tax_precondition_version: Optional[str] = None,
    ) -> ScoreResult:
        answer = next(a for a in self.answers if a.id == answer_id)
        question = self.questions[answer.question_id]

        if answer.answer_status == AnswerStatus.SKIPPED:
            result = ScoreResult(
                session_id=answer.session_id,
                question_id=answer.question_id,
                answer_id=answer.id,
                points=0,
                result_status=ResultStatus.SKIPPED,
                scored_at=datetime.utcnow(),
                scoring_mode=scoring_mode,
                basis_answer_id=None,
                basis="skipped",
                details=[],
            )
            self.score_results.append(result)
            return result

        candidates = self.acceptable_answers[answer.question_id]
        selected = None
        for candidate in candidates:
            if candidate.scoring_mode != scoring_mode:
                continue
            if question.mode == LearningMode.TAX_JOURNAL:
                if candidate.precondition != tax_precondition or candidate.precondition_version != tax_precondition_version:
                    continue
            selected = candidate
            break

        if not selected:
            result = ScoreResult(
                session_id=answer.session_id,
                question_id=answer.question_id,
                answer_id=answer.id,
                points=0,
                result_status=ResultStatus.UNSCORED,
                scored_at=datetime.utcnow(),
                scoring_mode=scoring_mode,
                basis_answer_id=None,
                basis="no acceptable answer matched",
                details=[],
            )
            self.score_results.append(result)
            return result

        rules = self.scoring_rules[answer.question_id].scoring_rule_data["elements"]
        total_max = sum(e["points"] for e in rules)
        awarded = 0
        details: List[ScoreResultDetail] = []

        for element in rules:
            key = element["key"]
            expect = selected.answer_data.get(key)
            actual = answer.answer_data.get(key)
            e_points = element["points"] if actual == expect else 0
            awarded += e_points
            details.append(
                ScoreResultDetail(
                    score_result_id="pending",
                    element=key,
                    max_points=element["points"],
                    awarded_points=e_points,
                    diff=f"expected={expect}, actual={actual}",
                )
            )

        points = int((awarded / total_max) * 100) if total_max else 0
        if points == 100:
            status = ResultStatus.CORRECT
        elif points == 0:
            status = ResultStatus.INCORRECT
        else:
            status = ResultStatus.PARTIAL

        result = ScoreResult(
            session_id=answer.session_id,
            question_id=answer.question_id,
            answer_id=answer.id,
            points=points,
            result_status=status,
            scored_at=datetime.utcnow(),
            scoring_mode=scoring_mode,
            basis_answer_id=selected.id,
            basis="matched acceptable answer",
            details=details,
        )
        for detail in details:
            detail.score_result_id = result.id
        self.score_results.append(result)
        return result

    def complete_session(self, session_id: str) -> None:
        session = self.learning_sessions[session_id]
        session.status = LearningSessionStatus.COMPLETED
        session.updated_at = datetime.utcnow()

    def get_explanations(self, question_id: str) -> List[ExplanationView]:
        return self.explanations[question_id]

    def get_ledger_impact(self, question_id: str) -> Dict:
        return self.ledger_effects[question_id].effect_data

    def get_history(self, user_id: str) -> List[LearningSession]:
        return [s for s in self.learning_sessions.values() if s.user_id == user_id]

    def summarize_weak_points(self, user_id: str) -> List[WeakPointSummary]:
        topic_points = defaultdict(list)
        for result in self.score_results:
            session = self.learning_sessions[result.session_id]
            if session.user_id != user_id:
                continue
            topic = self.questions[result.question_id].topic_id
            topic_points[topic].append(result.points)

        summaries: List[WeakPointSummary] = []
        for topic, points in topic_points.items():
            attempts = len(points)
            summaries.append(
                WeakPointSummary(
                    user_id=user_id,
                    topic_id=topic,
                    correct_rate=sum(1 for p in points if p == 100) / attempts,
                    avg_points=sum(points) / attempts,
                    attempts=attempts,
                )
            )
        return sorted(summaries, key=lambda s: s.avg_points)

    def import_questions_csv(self, csv_text: str, changed_by: str) -> ImportBatch:
        reader = csv.DictReader(io.StringIO(csv_text))
        rows = list(reader)
        success = 0
        failed = 0
        batch = ImportBatch(total_rows=len(rows), success_rows=0, failed_rows=0)
        self.import_batches.append(batch)

        for idx, row in enumerate(rows, start=1):
            try:
                mode = LearningMode(row["mode"])
                q_status = QuestionStatus(row["question_status"])
                c_type = CopyrightType(row["copyright_type"])
                if c_type == CopyrightType.UNCONFIRMED:
                    raise ValueError("copyright unconfirmed")
                q = Question(
                    title=row["title"],
                    body=row["body"],
                    mode=mode,
                    topic_id=row["topic_id"],
                    question_type=row["question_type"],
                    question_status=q_status,
                    copyright_type=c_type,
                    owner_user_id=row.get("owner_user_id") or None,
                    source_text=row.get("source_text") or None,
                    reconstructed_text=row.get("reconstructed_text") or None,
                )
                self.create_question(q, changed_by=changed_by)
                success += 1
            except Exception as exc:  # intentionally capture row-level failures
                failed += 1
                self.import_errors.append(
                    ImportError(batch_id=batch.id, row_no=idx, error_message=str(exc), row_data=row)
                )

        batch.success_rows = success
        batch.failed_rows = failed
        return batch

    def export_user_results_csv(self, user_id: str) -> str:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["session_id", "question_id", "points", "result_status", "scored_at"])
        for result in self.score_results:
            if self.learning_sessions[result.session_id].user_id != user_id:
                continue
            writer.writerow(
                [result.session_id, result.question_id, result.points, result.result_status.value, result.scored_at.isoformat()]
            )
        return output.getvalue()
