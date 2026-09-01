from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.enums import FinishedReason, InterviewStatus
from app.core.errors import (
    InterviewNotFoundError,
    InterviewStateConflictError,
    InvalidAnswerError,
    LLMQuestionGenerationError,
)
from app.models.answer import Answer
from app.models.interview import Interview
from app.models.interview_question import InterviewQuestion
from app.models.question import Question
from app.models.user import User
from app.repositories.interviews import InterviewRepository, QuestionRow
from app.repositories.knowledge import KnowledgeRepository
from app.repositories.llm_requests import LLMRequestRepository
from app.repositories.questions import QuestionRepository
from app.schemas.interviews import (
    AnswerFeedbackResponse,
    AnswerHistoryResponse,
    AnswerSubmitRequest,
    AnswerSubmitResponse,
    InterviewCreateRequest,
    InterviewCreateResponse,
    InterviewDetailResponse,
    InterviewFinishResponse,
    InterviewListItemResponse,
    InterviewQuestionResponse,
    InterviewResultResponse,
    InterviewResultSummary,
    KnowledgeNodeResponse,
    RecommendationResponse,
    SkillScoreResponse,
)
from app.services.knowledge import (
    KnowledgeEvidence,
    KnowledgeState,
    select_next_subtopic,
    update_knowledge,
)
from app.services.llm import (
    GeneratedQuestion,
    LLMEvaluationInput,
    LLMQuestionInput,
    LLMScoringClient,
    TopicCoverage,
    TopicWeight,
)
from app.services.ml import (
    MLKnowledgeNode,
    MLKnowledgeObservation,
    MLRecommendationClient,
    MLRecommendationInput,
)
from app.services.recommendations import (
    AnswerEvidenceInput,
    RecommendationService,
    SkillScoreInput,
)
from app.services.scoring import ScoringService


def percentage(score: int, max_score: int) -> int:
    return round(score * 100 / max_score) if max_score else 0


def question_response(
    interview_question: InterviewQuestion, question: Question
) -> InterviewQuestionResponse:
    return InterviewQuestionResponse(
        interview_question_id=interview_question.id,
        order_number=interview_question.order_number,
        skill=question.skill,
        text=question.text,
    )


def answer_feedback(answer: Answer) -> AnswerFeedbackResponse:
    return AnswerFeedbackResponse(
        id=answer.id,
        score=answer.score,
        max_score=answer.max_score,
        verdict=answer.verdict,
        feedback=answer.feedback,
        matched_points=answer.matched_points,
        missing_points=answer.missing_points,
        scoring_provider=answer.scoring_provider,
    )


def answer_history(row: QuestionRow) -> AnswerHistoryResponse:
    interview_question, question, answer = row
    if answer is None:
        raise ValueError("Cannot serialize an unanswered interview question")
    return AnswerHistoryResponse(
        **answer_feedback(answer).model_dump(),
        interview_question_id=interview_question.id,
        order_number=interview_question.order_number,
        question_text=question.text,
        skill=question.skill,
        answer_text=answer.answer_text,
    )


def knowledge_response(state: KnowledgeState) -> KnowledgeNodeResponse:
    return KnowledgeNodeResponse(
        topic=state.topic,
        subtopic=state.subtopic,
        score=state.score,
        confidence=state.confidence,
        evidence_count=state.evidence_count,
    )


def fallback_topics(question: Question) -> tuple[TopicWeight, ...]:
    return (TopicWeight(topic=question.skill, subtopic=question.skill, weight=1.0),)


def stored_topics(question: Question) -> tuple[TopicWeight, ...]:
    try:
        topics = tuple(TopicWeight(**item) for item in question.topic_weights)
    except (TypeError, ValueError):
        return ()
    return topics


def aggregate_skill_scores(
    rows: list[QuestionRow] | tuple[QuestionRow, ...],
) -> list[SkillScoreResponse]:
    totals: dict[str, tuple[int, int]] = {}
    for _, question, answer in rows:
        score, max_score = totals.get(question.skill, (0, 0))
        totals[question.skill] = (
            score + (answer.score if answer is not None else 0),
            max_score + question.max_score,
        )

    recommendation_service = RecommendationService()
    return [
        SkillScoreResponse(
            skill=skill,
            score=score,
            max_score=max_score,
            percentage=percentage(score, max_score),
            status=recommendation_service.skill_status(percentage(score, max_score)),
        )
        for skill, (score, max_score) in totals.items()
    ]


class InterviewService:
    def __init__(
        self,
        session: AsyncSession,
        settings: Settings,
        llm_scoring_client: LLMScoringClient,
        ml_recommendation_client: MLRecommendationClient,
    ) -> None:
        self.session = session
        self.settings = settings
        self.interviews = InterviewRepository(session)
        self.llm_requests = LLMRequestRepository(session)
        self.knowledge = KnowledgeRepository(session)
        self.questions = QuestionRepository(session)
        self.scoring = ScoringService()
        self.llm_scoring = llm_scoring_client
        self.ml_recommendations = ml_recommendation_client

    async def create(self, user: User, payload: InterviewCreateRequest) -> InterviewCreateResponse:
        user_id = user.id
        previous_questions = await self.interviews.previous_question_texts(
            user_id, payload.role.value, payload.level.value
        )
        await self.session.rollback()
        generate_baseline = getattr(self.llm_scoring, "generate_baseline_questions", None)
        if not self.llm_scoring.enabled or generate_baseline is None:
            raise LLMQuestionGenerationError("LLM question generation is unavailable")
        generation_attempt = await generate_baseline(
            role=payload.role.value,
            level=payload.level.value,
            previous_questions=previous_questions,
        )
        if generation_attempt.questions is None:
            raise LLMQuestionGenerationError("LLM could not generate baseline questions")

        assignments: list[tuple[InterviewQuestion, Question]] = []
        try:
            interview = Interview(
                user_id=user_id,
                role=payload.role.value,
                level=payload.level.value,
                status=InterviewStatus.IN_PROGRESS.value,
                target_questions_count=self.settings.interview_questions_count,
            )
            self.session.add(interview)
            await self.session.flush()

            for order_number, generated in enumerate(generation_attempt.questions, start=1):
                question = await self.questions.get_by_text(
                    interview.role, interview.level, generated.text
                )
                if question is None:
                    question = Question(
                        role=interview.role,
                        level=interview.level,
                        skill=generated.area,
                        source="generated_base",
                        target_subtopic=generated.topics[0].subtopic,
                        text=generated.text,
                        ideal_answer=generated.ideal_answer,
                        evaluation_points=list(generated.evaluation_points),
                        topic_weights=[
                            {
                                "topic": item.topic,
                                "subtopic": item.subtopic,
                                "weight": item.weight,
                            }
                            for item in generated.topics
                        ],
                        max_score=10,
                        is_active=False,
                    )
                    self.session.add(question)
                    await self.session.flush()
                else:
                    question.skill = generated.area
                    question.source = "generated_base"
                    question.target_subtopic = generated.topics[0].subtopic
                    question.ideal_answer = generated.ideal_answer
                    question.evaluation_points = list(generated.evaluation_points)
                    question.topic_weights = [
                        {
                            "topic": item.topic,
                            "subtopic": item.subtopic,
                            "weight": item.weight,
                        }
                        for item in generated.topics
                    ]
                    question.is_active = False
                assignment = InterviewQuestion(
                    interview_id=interview.id,
                    question_id=question.id,
                    order_number=order_number,
                )
                self.session.add(assignment)
                assignments.append((assignment, question))
            await self.session.flush()
            self.llm_requests.add(
                interview.id,
                question_id=assignments[0][1].id,
                provider=generation_attempt.provider,
                model=generation_attempt.model,
                prompt_type="generate_baseline_questions",
                latency_ms=generation_attempt.latency_ms,
                success=True,
                error=None,
            )
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise

        first_assignment, first_question = assignments[0]
        return InterviewCreateResponse(
            id=interview.id,
            role=interview.role,
            level=interview.level,
            status=interview.status,
            total_questions=interview.target_questions_count,
            answered_questions=0,
            current_question=question_response(first_assignment, first_question),
            created_at=interview.created_at,
        )

    async def list(self, user: User) -> list[InterviewListItemResponse]:
        rows = await self.interviews.list_owned_summaries(user.id)
        return [
            InterviewListItemResponse(
                id=interview.id,
                role=interview.role,
                level=interview.level,
                status=interview.status,
                total_score=interview.total_score,
                max_score=max(max_score, interview.target_questions_count * 10),
                percentage=percentage(
                    interview.total_score,
                    max(max_score, interview.target_questions_count * 10),
                ),
                created_at=interview.created_at,
                finished_at=interview.finished_at,
            )
            for interview, max_score in rows
        ]

    async def detail(self, user: User, interview_id: UUID) -> InterviewDetailResponse:
        interview = await self._owned_or_raise(user.id, interview_id)
        rows = await self.interviews.question_rows(interview.id)
        answered_rows = [row for row in rows if row[2] is not None]
        current_row = next((row for row in rows if row[2] is None), None)
        current_question = (
            question_response(current_row[0], current_row[1])
            if current_row is not None and interview.status == InterviewStatus.IN_PROGRESS
            else None
        )
        knowledge = await self.knowledge.load(user.id, interview.role, interview.level)
        return InterviewDetailResponse(
            id=interview.id,
            role=interview.role,
            level=interview.level,
            status=interview.status,
            total_score=interview.total_score,
            total_questions=interview.target_questions_count,
            answered_questions=len(answered_rows),
            current_question=current_question,
            answers=[answer_history(row) for row in answered_rows],
            knowledge_graph=[knowledge_response(state) for state in knowledge],
            created_at=interview.created_at,
            finished_at=interview.finished_at,
        )

    async def submit_answer(
        self, user: User, interview_id: UUID, payload: AnswerSubmitRequest
    ) -> AnswerSubmitResponse:
        user_id = user.id
        analysis_attempt = None
        generation_attempt = None
        try:
            interview = await self._owned_or_raise(user_id, interview_id)
            if interview.status != InterviewStatus.IN_PROGRESS:
                raise InterviewStateConflictError("Interview is already finished")

            rows = await self.interviews.question_rows(interview.id)
            current_index = next((i for i, row in enumerate(rows) if row[2] is None), None)
            if current_index is None:
                raise InterviewStateConflictError("Interview has no unanswered question")

            current_assignment, question, _ = rows[current_index]
            if current_assignment.id != payload.interview_question_id:
                raise InterviewStateConflictError(
                    "Only the current unanswered question can be answered"
                )

            try:
                fallback_outcome = self.scoring.evaluate(question, payload.answer_text)
            except ValueError as error:
                raise InvalidAnswerError("Answer must contain meaningful text") from error

            question_input = LLMQuestionInput(
                role=interview.role,
                level=interview.level,
                skill=question.skill,
                question_text=question.text,
                ideal_answer=question.ideal_answer,
                evaluation_points=tuple(question.evaluation_points),
            )
            topics = stored_topics(question)
            knowledge_before = await self.knowledge.load(user_id, interview.role, interview.level)
            expected_assignment_id = current_assignment.id
            expected_question_id = question.id
            role = interview.role
            level = interview.level
            target_questions_count = interview.target_questions_count
            previous_questions = tuple(row[1].text for row in rows)
            has_assigned_next = current_index + 1 < len(rows)
            will_finish = current_index + 1 >= target_questions_count
            await self.session.rollback()
        except Exception:
            await self.session.rollback()
            raise

        if not topics:
            analyze = getattr(self.llm_scoring, "analyze_question", None)
            if self.llm_scoring.enabled and analyze is not None:
                analysis_attempt = await analyze(question_input)
                topics = analysis_attempt.topics or ()
        topics = topics or (
            TopicWeight(topic=question_input.skill, subtopic=question_input.skill, weight=1.0),
        )
        llm_input = LLMEvaluationInput(
            role=question_input.role,
            level=question_input.level,
            skill=question_input.skill,
            question_text=question_input.question_text,
            ideal_answer=question_input.ideal_answer,
            evaluation_points=question_input.evaluation_points,
            user_answer=payload.answer_text,
            topics=topics,
        )
        attempt = await self.llm_scoring.evaluate(llm_input) if self.llm_scoring.enabled else None
        outcome = attempt.outcome if attempt is not None and attempt.outcome else fallback_outcome
        topic_coverage = (
            attempt.topic_coverage
            if attempt is not None and attempt.success and attempt.topic_coverage
            else tuple(
                TopicCoverage(
                    topic=item.topic,
                    subtopic=item.subtopic,
                    coverage=fallback_outcome.score / fallback_outcome.max_score,
                )
                for item in topics
            )
        )
        coverage_by_key = {
            (item.topic.casefold(), item.subtopic.casefold()): item.coverage
            for item in topic_coverage
        }
        evidence = [
            KnowledgeEvidence(
                topic=item.topic,
                subtopic=item.subtopic,
                coverage=coverage_by_key[(item.topic.casefold(), item.subtopic.casefold())],
                weight=item.weight,
            )
            for item in topics
        ]
        knowledge_after = update_knowledge(knowledge_before, evidence)
        target = select_next_subtopic(knowledge_after)

        update_knowledge_model = getattr(self.ml_recommendations, "update_knowledge", None)
        if update_knowledge_model is not None and getattr(
            self.ml_recommendations, "enabled", False
        ):
            ml_result = await update_knowledge_model(
                nodes=[
                    MLKnowledgeNode(
                        topic=state.topic,
                        subtopic=state.subtopic,
                        score=state.score,
                        confidence=state.confidence,
                        evidence_count=state.evidence_count,
                        evidence_weight=state.evidence_weight,
                    )
                    for state in knowledge_before
                ],
                observations=[
                    MLKnowledgeObservation(
                        topic=item.topic,
                        subtopic=item.subtopic,
                        question_weight=item.weight,
                        coverage=item.coverage,
                    )
                    for item in evidence
                ],
            )
            if ml_result is not None:
                nodes, target_pair = ml_result
                knowledge_after = [KnowledgeState(**node.model_dump()) for node in nodes]
                target = next(
                    state
                    for state in knowledge_after
                    if (state.topic.casefold(), state.subtopic.casefold())
                    == (target_pair[0].casefold(), target_pair[1].casefold())
                )

        generated: GeneratedQuestion | None = None
        needs_generated_next = not has_assigned_next and not will_finish
        if needs_generated_next and target is not None:
            generate = getattr(self.llm_scoring, "generate_question", None)
            if self.llm_scoring.enabled and generate is not None:
                generation_attempt = await generate(
                    role=role,
                    level=level,
                    topic=target.topic,
                    subtopic=target.subtopic,
                    previous_questions=previous_questions,
                )
                generated = generation_attempt.question
        if needs_generated_next and generated is None:
            raise LLMQuestionGenerationError("LLM could not generate the next question")

        try:
            interview = await self._owned_or_raise(user_id, interview_id, for_update=True)
            if interview.status != InterviewStatus.IN_PROGRESS:
                raise InterviewStateConflictError("Interview is already finished")

            rows = await self.interviews.question_rows(interview.id)
            current_index = next((i for i, row in enumerate(rows) if row[2] is None), None)
            if current_index is None:
                raise InterviewStateConflictError("Interview has no unanswered question")

            current_assignment, current_question, _ = rows[current_index]
            if (
                current_assignment.id != expected_assignment_id
                or current_assignment.id != payload.interview_question_id
                or current_question.id != expected_question_id
            ):
                raise InterviewStateConflictError(
                    "Only the current unanswered question can be answered"
                )

            answer = Answer(
                interview_id=interview.id,
                interview_question_id=current_assignment.id,
                answer_text=payload.answer_text,
                score=outcome.score,
                max_score=outcome.max_score,
                verdict=outcome.verdict.value,
                feedback=outcome.feedback,
                matched_points=outcome.matched_points,
                missing_points=outcome.missing_points,
                topic_coverage=[
                    {
                        "topic": item.topic,
                        "subtopic": item.subtopic,
                        "coverage": item.coverage,
                    }
                    for item in topic_coverage
                ],
                scoring_provider=outcome.provider,
                llm_score=outcome.score if attempt is not None and attempt.success else None,
                keyword_score=fallback_outcome.score,
            )
            current_question.topic_weights = [
                {"topic": item.topic, "subtopic": item.subtopic, "weight": item.weight}
                for item in topics
            ]
            self.session.add(answer)
            interview.total_score += outcome.score
            await self.session.flush()
            await self.knowledge.upsert(user_id, interview.role, interview.level, knowledge_after)
            if attempt is not None:
                self.llm_requests.add(
                    interview.id,
                    answer.id,
                    question_id=current_question.id,
                    provider=attempt.provider,
                    model=attempt.model,
                    prompt_type="evaluate_answer",
                    latency_ms=attempt.latency_ms,
                    success=attempt.success,
                    error=attempt.error,
                )
            if analysis_attempt is not None:
                self.llm_requests.add(
                    interview.id,
                    answer.id,
                    question_id=current_question.id,
                    provider=analysis_attempt.provider,
                    model=analysis_attempt.model,
                    prompt_type="analyze_question",
                    latency_ms=analysis_attempt.latency_ms,
                    success=analysis_attempt.success,
                    error=analysis_attempt.error,
                )

            next_row = rows[current_index + 1] if current_index + 1 < len(rows) else None
            next_question_model: Question | None = None
            if next_row is None and current_index + 1 < interview.target_questions_count:
                if generated is not None and target is not None:
                    next_question_model = await self.questions.get_by_text(
                        interview.role, interview.level, generated.text
                    )
                    if next_question_model is None:
                        next_question_model = Question(
                            role=interview.role,
                            level=interview.level,
                            skill=target.topic,
                            source="generated_adaptive",
                            target_subtopic=target.subtopic,
                            text=generated.text,
                            ideal_answer=generated.ideal_answer,
                            evaluation_points=list(generated.evaluation_points),
                            topic_weights=[
                                {
                                    "topic": item.topic,
                                    "subtopic": item.subtopic,
                                    "weight": item.weight,
                                }
                                for item in generated.topics
                            ],
                            max_score=10,
                            is_active=False,
                        )
                        self.session.add(next_question_model)
                        await self.session.flush()
                if next_question_model is not None:
                    assignment = InterviewQuestion(
                        interview_id=interview.id,
                        question_id=next_question_model.id,
                        order_number=len(rows) + 1,
                    )
                    self.session.add(assignment)
                    await self.session.flush()
                    next_row = (assignment, next_question_model, None)

            if generation_attempt is not None:
                self.llm_requests.add(
                    interview.id,
                    answer.id,
                    question_id=next_question_model.id if next_question_model is not None else None,
                    provider=generation_attempt.provider,
                    model=generation_attempt.model,
                    prompt_type="generate_question",
                    latency_ms=generation_attempt.latency_ms,
                    success=generation_attempt.success,
                    error=generation_attempt.error,
                )

            if next_row is None:
                interview.status = InterviewStatus.FINISHED.value
                interview.finished_reason = FinishedReason.COMPLETED.value
                interview.finished_at = datetime.now(UTC)
                next_question = None
                result_url = f"/api/v1/interviews/{interview.id}/result"
            else:
                next_question = question_response(next_row[0], next_row[1])
                result_url = None
            await self.session.commit()

            return AnswerSubmitResponse(
                answer=answer_feedback(answer),
                interview_status=interview.status,
                next_question=next_question,
                result_url=result_url,
            )
        except IntegrityError as error:
            await self.session.rollback()
            raise InterviewStateConflictError("This question already has an answer") from error
        except Exception:
            await self.session.rollback()
            raise

    async def finish(self, user: User, interview_id: UUID) -> InterviewFinishResponse:
        try:
            interview = await self._owned_or_raise(user.id, interview_id, for_update=True)
            if interview.status != InterviewStatus.IN_PROGRESS:
                raise InterviewStateConflictError("Interview is already finished")
            rows = await self.interviews.question_rows(interview.id)
            max_score = max(
                sum(question.max_score for _, question, _ in rows),
                interview.target_questions_count * 10,
            )
            interview.status = InterviewStatus.FINISHED.value
            interview.finished_reason = FinishedReason.MANUAL.value
            interview.finished_at = datetime.now(UTC)
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise

        return InterviewFinishResponse(
            id=interview.id,
            status=interview.status,
            finished_reason=interview.finished_reason,
            total_score=interview.total_score,
            max_score=max_score,
            percentage=percentage(interview.total_score, max_score),
            result_url=f"/api/v1/interviews/{interview.id}/result",
        )

    async def result(self, user: User, interview_id: UUID) -> InterviewResultResponse:
        interview = await self._owned_or_raise(user.id, interview_id)
        if interview.status != InterviewStatus.FINISHED:
            raise InterviewStateConflictError("Result is available only for a finished interview")
        rows = await self.interviews.question_rows(interview.id)
        max_score = max(
            sum(question.max_score for _, question, _ in rows),
            interview.target_questions_count * 10,
        )
        if interview.finished_at is None or interview.finished_reason is None:
            raise InterviewStateConflictError("Finished interview metadata is incomplete")

        skill_scores = aggregate_skill_scores(list(rows))
        answered_rows = [row for row in rows if row[2] is not None]
        knowledge = await self.knowledge.load(user.id, interview.role, interview.level)
        recommendation_service = RecommendationService()
        recommendation_inputs = [
            SkillScoreInput(
                skill=item.skill,
                score=item.score,
                max_score=item.max_score,
                percentage=item.percentage,
            )
            for item in skill_scores
        ]
        answer_evidence = [
            AnswerEvidenceInput(
                skill=question.skill,
                answer_text=answer.answer_text,
                score=answer.score,
                max_score=answer.max_score,
                verdict=answer.verdict,
                matched_points=tuple(answer.matched_points),
                missing_points=tuple(answer.missing_points),
            )
            for _, question, answer in answered_rows
            if answer is not None
        ]
        recommendations = recommendation_service.generate(
            role=interview.role,
            level=interview.level,
            answers=answer_evidence,
            skill_scores=recommendation_inputs,
        )
        if len(recommendations) > 1:
            ranking = await self.ml_recommendations.rank(
                recommendations=[
                    MLRecommendationInput(
                        skill=item.skill,
                        priority=item.priority.value,
                        current_percentage=item.current_percentage,
                        topics_count=len(item.topics_to_learn),
                    )
                    for item in recommendations
                ],
            )
            if ranking is not None:
                by_skill = {item.skill: item for item in recommendations}
                recommendations = [by_skill[skill] for skill in ranking]
        return InterviewResultResponse(
            interview=InterviewResultSummary(
                id=interview.id,
                role=interview.role,
                level=interview.level,
                status=interview.status,
                finished_reason=interview.finished_reason,
                total_score=interview.total_score,
                max_score=max_score,
                percentage=percentage(interview.total_score, max_score),
                started_at=interview.started_at,
                finished_at=interview.finished_at,
            ),
            skill_scores=skill_scores,
            answers=[answer_history(row) for row in answered_rows],
            recommendations=[
                RecommendationResponse(
                    skill=item.skill,
                    priority=item.priority,
                    current_percentage=item.current_percentage,
                    reason=item.reason,
                    topics_to_learn=list(item.topics_to_learn),
                    practice_tasks=list(item.practice_tasks),
                )
                for item in recommendations
            ],
            knowledge_graph=[knowledge_response(state) for state in knowledge],
        )

    async def _owned_or_raise(
        self, user_id: UUID, interview_id: UUID, *, for_update: bool = False
    ) -> Interview:
        interview = await self.interviews.get_owned(interview_id, user_id, for_update=for_update)
        if interview is None:
            raise InterviewNotFoundError
        return interview
