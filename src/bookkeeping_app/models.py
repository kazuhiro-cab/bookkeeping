from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
from uuid import uuid4


class LearningMode(str, Enum):
    SINGLE_ENTRY = "単式簿記モード"
    DOUBLE_ENTRY = "複式簿記モード"
    TAX_JOURNAL = "税金仕訳学習モード"
    WHITE_RETURN = "白色申告学習モード"
    BLUE_RETURN = "青色申告学習モード"
    GRADE1_ACCOUNTING = "日商簿記1級 会計学モード"
    GRADE1_COMMERCIAL = "日商簿記1級 商業簿記モード"
    GRADE1_COST = "日商簿記1級 原価計算モード"
    GRADE1_INDUSTRIAL = "日商簿記1級 工業簿記モード"
    CROSS_REVIEW = "横断復習モード"
    MOCK_EXAM = "模擬試験モード"


class LearningSessionStatus(str, Enum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    TIMED_OUT = "timed_out"
    ABANDONED = "abandoned"


class QuestionStatus(str, Enum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    PUBLISHABLE = "publishable"
    SUSPENDED = "suspended"
    RETIRED = "retired"


class AnswerStatus(str, Enum):
    TEMPORARY_SAVED = "temporary_saved"
    SUBMITTED = "submitted"
    SKIPPED = "skipped"
    EXPIRED = "expired"


class ResultStatus(str, Enum):
    CORRECT = "correct"
    PARTIAL = "partial"
    INCORRECT = "incorrect"
    UNSCORED = "unscored"
    SKIPPED = "skipped"


class CopyrightType(str, Enum):
    LICENSED = "利用許諾確認済"
    USER_OWNED = "ユーザー私有教材"
    ORIGINAL = "独自作成"
    UNCONFIRMED = "利用条件未確認"
    PROHIBITED = "収録不可"


@dataclass
class User:
    name: str
    id: str = field(default_factory=lambda: str(uuid4()))


@dataclass
class StudyProfile:
    user_id: str
    active_mode: LearningMode
    id: str = field(default_factory=lambda: str(uuid4()))


@dataclass
class LearningSession:
    user_id: str
    mode: LearningMode
    status: LearningSessionStatus = LearningSessionStatus.IN_PROGRESS
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class AcceptableAnswer:
    question_id: str
    scoring_mode: str
    answer_data: Dict
    precondition: Optional[str] = None
    precondition_version: Optional[str] = None
    apply_condition: Optional[str] = None
    id: str = field(default_factory=lambda: str(uuid4()))


@dataclass
class ScoringRule:
    question_id: str
    scoring_rule_data: Dict
    id: str = field(default_factory=lambda: str(uuid4()))


@dataclass
class Question:
    title: str
    body: str
    mode: LearningMode
    topic_id: str
    question_type: str
    copyright_type: CopyrightType
    owner_user_id: Optional[str]
    question_status: QuestionStatus = QuestionStatus.DRAFT
    source_text: Optional[str] = None
    reconstructed_text: Optional[str] = None
    id: str = field(default_factory=lambda: str(uuid4()))


@dataclass
class QuestionRevision:
    question_id: str
    changed_by: str
    reason: str
    before: Dict
    after: Dict
    id: str = field(default_factory=lambda: str(uuid4()))
    changed_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class SessionQuestion:
    session_id: str
    question_id: str
    sequence_no: int
    id: str = field(default_factory=lambda: str(uuid4()))


@dataclass
class Answer:
    session_id: str
    question_id: str
    answer_data: Dict
    answer_status: AnswerStatus
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ScoreResultDetail:
    score_result_id: str
    element: str
    max_points: int
    awarded_points: int
    diff: str
    id: str = field(default_factory=lambda: str(uuid4()))


@dataclass
class ScoreResult:
    session_id: str
    question_id: str
    answer_id: str
    points: int
    result_status: ResultStatus
    scored_at: datetime
    scoring_mode: str
    basis_answer_id: Optional[str]
    basis: str
    details: List[ScoreResultDetail]
    id: str = field(default_factory=lambda: str(uuid4()))


@dataclass
class LedgerEffectTemplate:
    question_id: str
    effect_data: Dict
    id: str = field(default_factory=lambda: str(uuid4()))


@dataclass
class ExplanationView:
    question_id: str
    level: str
    explanation: str
    common_mistakes: List[str]
    fs_impact: str
    cost_impact: str
    id: str = field(default_factory=lambda: str(uuid4()))


@dataclass
class WeakPointSummary:
    user_id: str
    topic_id: str
    correct_rate: float
    avg_points: float
    attempts: int


@dataclass
class ImportBatch:
    total_rows: int
    success_rows: int
    failed_rows: int
    id: str = field(default_factory=lambda: str(uuid4()))


@dataclass
class ImportError:
    batch_id: str
    row_no: int
    error_message: str
    row_data: Dict
    id: str = field(default_factory=lambda: str(uuid4()))
