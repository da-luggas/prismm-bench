export const QUESTION_TYPES = {
  default: "default",
  binary_consistent: "binary_consistent",
  binary_inconsistent: "binary_inconsistent",
  edit: "edit",
} as const

export type QuestionType = keyof typeof QUESTION_TYPES

export function getQuestionType(): QuestionType {
  const envType = process.env.NEXT_PUBLIC_QUESTION_TYPE as QuestionType
  return envType && envType in QUESTION_TYPES ? envType : "default"
}

export function getQuestionTypeDescription(type: QuestionType): string {
  const descriptions = {
    default: "General inconsistency identification questions",
    binary_consistent: "Yes/No questions about figure-text consistency",
    binary_inconsistent: "Yes/No questions about figure-text inconsistency",
    edit: "Questions about how to resolve inconsistencies",
  }
  return descriptions[type]
}

export const SURVEY_CONFIG = {
  questionsPerSurvey: 10,
  regularQuestions: 5,
  pdfQuestions: 5,
  shuffleOptions: true,
  shuffleQuestions: true,
} as const
