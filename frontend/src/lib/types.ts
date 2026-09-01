export type RoleSlug = "backend" | "ml_engineer" | "llm_engineer";

export type Role = RoleSlug;

export type Level = "junior" | "middle" | "senior";

export type InterviewStatus = "in_progress" | "finished";

export type FinishedReason = "completed" | "manual";

export type Verdict = "correct" | "partially_correct" | "incorrect";

export type SkillStatus = "good" | "need_repeat" | "weak";

export type RecommendationPriority = "high" | "medium";

export interface RegisterRequest {
  email: string;
  password: string;
  full_name?: string | null;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface User {
  id: string;
  email: string;
  full_name: string | null;
  created_at: string;
}

export interface RoleOption {
  slug: RoleSlug;
  title: string;
  levels: Level[];
}

export interface InterviewQuestion {
  interview_question_id: string;
  order_number: number;
  skill: string;
  text: string;
}

export interface AnswerFeedback {
  id: string;
  score: number;
  max_score: number;
  verdict: Verdict;
  feedback: string;
  matched_points: string[];
  missing_points: string[];
  scoring_provider: string;
}

export interface AnswerHistory extends AnswerFeedback {
  interview_question_id: string;
  order_number: number;
  question_text: string;
  skill: string;
  answer_text: string;
}

export interface KnowledgeNode {
  topic: string;
  subtopic: string;
  score: number;
  confidence: number;
  evidence_count: number;
}

export interface InterviewCreateRequest {
  role: RoleSlug;
  level: Level;
}

export interface InterviewCreateResponse {
  id: string;
  role: RoleSlug;
  level: Level;
  status: InterviewStatus;
  total_questions: number;
  answered_questions: number;
  current_question: InterviewQuestion;
  created_at: string;
}

export interface InterviewListItem {
  id: string;
  role: RoleSlug;
  level: Level;
  status: InterviewStatus;
  total_score: number;
  max_score: number;
  percentage: number;
  created_at: string;
  finished_at: string | null;
}

export interface InterviewDetail {
  id: string;
  role: RoleSlug;
  level: Level;
  status: InterviewStatus;
  total_score: number;
  total_questions: number;
  answered_questions: number;
  current_question: InterviewQuestion | null;
  answers: AnswerHistory[];
  knowledge_graph: KnowledgeNode[];
  created_at: string;
  finished_at: string | null;
}

export interface AnswerSubmitRequest {
  interview_question_id: string;
  answer_text: string;
}

export interface AnswerSubmitResponse {
  answer: AnswerFeedback;
  interview_status: InterviewStatus;
  next_question: InterviewQuestion | null;
  result_url: string | null;
}

export interface InterviewFinishResponse {
  id: string;
  status: InterviewStatus;
  finished_reason: FinishedReason;
  total_score: number;
  max_score: number;
  percentage: number;
  result_url: string;
}

export interface InterviewResultSummary {
  id: string;
  role: RoleSlug;
  level: Level;
  status: InterviewStatus;
  finished_reason: FinishedReason;
  total_score: number;
  max_score: number;
  percentage: number;
  started_at: string;
  finished_at: string;
}

export interface SkillScore {
  skill: string;
  score: number;
  max_score: number;
  percentage: number;
  status: SkillStatus;
}

export interface Recommendation {
  skill: string;
  priority: RecommendationPriority;
  current_percentage: number;
  reason: string;
  topics_to_learn: string[];
  practice_tasks: string[];
}

export interface InterviewResult {
  interview: InterviewResultSummary;
  skill_scores: SkillScore[];
  answers: AnswerHistory[];
  recommendations: Recommendation[];
  knowledge_graph: KnowledgeNode[];
}

export interface AnalyticsSummary {
  total_interviews: number;
  finished_interviews: number;
  average_percentage: number | null;
  best_role: RoleSlug | null;
  strongest_skill: string | null;
  weakest_skills: string[];
}

export interface AnalyticsSkill {
  skill: string;
  average_percentage: number;
  answers_count: number;
}

export interface AnalyticsProgress {
  interview_id: string;
  role: RoleSlug;
  level: Level;
  finished_at: string;
  percentage: number;
}

export interface ApiErrorBody {
  detail?: unknown;
}
