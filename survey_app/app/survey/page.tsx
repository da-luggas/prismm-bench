"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import { Label } from "@/components/ui/label"
import { Progress } from "@/components/ui/progress"
import { Badge } from "@/components/ui/badge"
import { useToast } from "@/hooks/use-toast"
import { getQuestionType, getQuestionTypeDescription, SURVEY_CONFIG } from "@/lib/survey-config"
import annotationsData from "@/data/annotations.json"
import Image from "next/image"

interface InconsistencyPart {
  type: "text" | "image"
  page?: number
  content?: string
  line?: number
  image_id?: string
  bbox?: {
    x: number
    y: number
    width: number
    height: number
  }
}

interface MCQOption {
  question: string
  correct: string
  incorrect: string[]
}

interface Annotation {
  inconsistency_parts: InconsistencyPart[]
  review_text: string
  category: string
  description: string
  confidence: number
  mcq: {
    [key: string]: MCQOption
  }
  severity: number
  visual_elements?: string[]
}

interface SurveyQuestion {
  id: string
  annotationIndex: number
  inconsistency: Annotation
  question: string
  options: string[]
  correctAnswer: string
  isPdfQuestion: boolean
  pdfUrl?: string
  textLineNumber?: number
  visualElements?: string[]
}

export default function SurveyPage() {
  const [questions, setQuestions] = useState<SurveyQuestion[]>([])
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0)
  const [selectedAnswer, setSelectedAnswer] = useState("")
  const [answers, setAnswers] = useState<string[]>([])
  const [answerTimes, setAnswerTimes] = useState<number[]>([])
  const [questionStartTime, setQuestionStartTime] = useState<number>(Date.now())
  const [isLoading, setIsLoading] = useState(true)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [questionType, setQuestionType] = useState<string>("default")
  const { toast } = useToast()

  useEffect(() => {
    async function fetchQuestions() {
      const configuredQuestionType = getQuestionType()
      setQuestionType(configuredQuestionType)

      // Get user email from localStorage
      const userInfo = JSON.parse(localStorage.getItem("userInfo") || "{}")
      const email = userInfo.email

      let answeredIds: string[] = []
      if (email) {
        try {
          const res = await fetch("/api/answered-inconsistencies", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email }),
          })
          if (res.ok) {
            const data = await res.json()
            answeredIds = data.answeredIds || []
          }
        } catch (e) {
          // ignore, fallback to showing all
        }
      }

      // Select random annotations, excluding already answered
  const allAnnotations = Object.entries(annotationsData)
      const selectedQuestions: SurveyQuestion[] = []

      // Flatten all annotations with their IDs
      const flatAnnotations: { id: string; index: number; annotation: Annotation }[] = []
      allAnnotations.forEach(([id, annotations]) => {
        (annotations as any[]).forEach((annotation, index) => {
          // Patch the type property to be the expected literal type if needed
          if (annotation && Array.isArray(annotation.inconsistency_parts)) {
            annotation.inconsistency_parts = annotation.inconsistency_parts.map((part: any) => {
              if (part.type !== "text" && part.type !== "image") {
                // Try to infer type from available fields
                if (typeof part.content === "string") return { ...part, type: "text" };
                if (typeof part.image_id === "string") return { ...part, type: "image" };
              }
              return part;
            });
          }
          flatAnnotations.push({ id, index, annotation: annotation as Annotation })
        })
      })

      // Exclude already answered
      const filtered = flatAnnotations.filter((item) => !answeredIds.includes(item.id))
      const shuffled = SURVEY_CONFIG.shuffleQuestions ? filtered.sort(() => Math.random() - 0.5) : filtered
      
      // Split into regular and PDF questions
      const regularSelected = shuffled.slice(0, SURVEY_CONFIG.regularQuestions)
      const pdfSelected = shuffled.slice(SURVEY_CONFIG.regularQuestions, SURVEY_CONFIG.regularQuestions + SURVEY_CONFIG.pdfQuestions)

      // Create regular questions
      regularSelected.forEach((item) => {
        const mcq = item.annotation.mcq[configuredQuestionType] || item.annotation.mcq.default
        if (mcq) {
          const allOptions = [mcq.correct, ...mcq.incorrect]
          const shuffledOptions = SURVEY_CONFIG.shuffleOptions ? allOptions.sort(() => Math.random() - 0.5) : allOptions

          selectedQuestions.push({
            id: item.id,
            annotationIndex: item.index,
            inconsistency: item.annotation,
            question: mcq.question,
            options: shuffledOptions,
            correctAnswer: mcq.correct,
            isPdfQuestion: false,
          })
        }
      })

      // Create PDF questions
      pdfSelected.forEach((item) => {
        const mcq = item.annotation.mcq[configuredQuestionType] || item.annotation.mcq.default
        if (mcq) {
          const allOptions = [mcq.correct, ...mcq.incorrect]
          const shuffledOptions = SURVEY_CONFIG.shuffleOptions ? allOptions.sort(() => Math.random() - 0.5) : allOptions

          // Extract text line numbers and visual elements
          const textParts = item.annotation.inconsistency_parts.filter(part => part.type === "text")
          const textLineNumber = textParts.length > 0 ? textParts[0].line : undefined
          const visualElements = item.annotation.visual_elements || []

          selectedQuestions.push({
            id: item.id,
            annotationIndex: item.index,
            inconsistency: item.annotation,
            question: mcq.question,
            options: shuffledOptions,
            correctAnswer: mcq.correct,
            isPdfQuestion: true,
            pdfUrl: `https://openreview.net/pdf?id=${item.id}`,
            textLineNumber,
            visualElements,
          })
        }
      })

      setQuestions(selectedQuestions)
      setIsLoading(false)
      setQuestionStartTime(Date.now()) // Start timing for first question
    }
    fetchQuestions()
  }, [])

  // Reset timer when question changes
  useEffect(() => {
    if (questions.length > 0) {
      setQuestionStartTime(Date.now())
    }
  }, [currentQuestionIndex, questions.length])

  const handleNextQuestion = async () => {
    const currentTime = Date.now()
    const timeSpent = currentTime - questionStartTime
    const newAnswers = [...answers, selectedAnswer]
    const newAnswerTimes = [...answerTimes, timeSpent]
    
    setAnswers(newAnswers)
    setAnswerTimes(newAnswerTimes)

    if (currentQuestionIndex < questions.length - 1) {
      setCurrentQuestionIndex((prev) => prev + 1)
      setSelectedAnswer("")
    } else {
      // Survey completed - save results
      setIsSubmitting(true)

      try {
        const userInfo = JSON.parse(localStorage.getItem("userInfo") || "{}")
        const results = questions.map((q, index) => ({
          inconsistency_id: q.id,
          inconsistency_index: q.annotationIndex,
          question: q.question,
          correct_answer: q.correctAnswer,
          user_answer: index < newAnswers.length ? newAnswers[index] : selectedAnswer,
          is_correct: (index < newAnswers.length ? newAnswers[index] : selectedAnswer) === q.correctAnswer,
          is_pdf_question: q.isPdfQuestion,
          answer_time_ms: index < newAnswerTimes.length ? newAnswerTimes[index] : (Date.now() - questionStartTime),
          user_info: userInfo,
        }))

        const response = await fetch("/api/submit-survey", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(results),
        })

        if (!response.ok) {
          throw new Error("Failed to submit survey")
        }

        // Store results locally as backup
        localStorage.setItem("surveyResults", JSON.stringify(results))

        toast({
          title: "Survey Submitted",
          description: "Your responses have been saved successfully.",
        })

        window.location.href = "/thank-you"
      } catch (error) {
        console.error("Error submitting survey:", error)
        toast({
          title: "Submission Error",
          description: "There was an error saving your responses. Please try again.",
          variant: "destructive",
        })
      } finally {
        setIsSubmitting(false)
      }
    }
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4"></div>
          <p>Loading survey questions...</p>
        </div>
      </div>
    )
  }

  if (questions.length === 0) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <Card className="w-full max-w-md">
          <CardContent className="pt-6 text-center">
            <p>No questions available. Please try again later.</p>
            <Button onClick={() => (window.location.href = "/")} className="mt-4">
              Go Back
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  const currentQuestion = questions[currentQuestionIndex]
  const progress = ((currentQuestionIndex + 1) / questions.length) * 100

  return (
    <div className="min-h-screen bg-background p-4">
      <div className="max-w-4xl mx-auto space-y-6">
        <div className="text-center">
          <h1 className="text-2xl font-bold mb-2">Research Survey</h1>
          <div className="flex items-center justify-center gap-2 mb-2">
            <p className="text-muted-foreground">
              Question {currentQuestionIndex + 1} of {questions.length}
            </p>
          </div>          <Progress value={progress} className="w-full" />
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Context</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {currentQuestion.isPdfQuestion ? (
              <div className="space-y-4">
                <div className="border rounded-lg p-8 bg-muted/50 text-center space-y-4">
                  <div className="space-y-2">
                    <h3 className="text-lg font-semibold">PDF Document</h3>
                    <p className="text-muted-foreground">
                      For this question, you can scroll the whole paper PDF to answer.
                    </p>
                  </div>
                  <Button 
                    onClick={() => window.open(currentQuestion.pdfUrl, '_blank')}
                    size="lg"
                    className="inline-flex items-center gap-2"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                    </svg>
                    Open PDF Document
                  </Button>
                </div>
                <div className="my-6 p-5 bg-blue-50 border-l-4 border-blue-300 rounded-lg text-blue-900 flex flex-col gap-2">
                  <span className="font-medium">💡 <strong>Pay attention to the following parts of the paper:</strong></span>
                  {currentQuestion.textLineNumber && (
                    <span>
                      <strong>Text parts:</strong> From Line {currentQuestion.textLineNumber}
                    </span>
                  )}
                  {currentQuestion.visualElements && currentQuestion.visualElements.length > 0 && (
                    <span>
                      <strong>Visual parts:</strong> {currentQuestion.visualElements.map(element => 
                        element.startsWith("(") && element.endsWith(")") ? `Equation ${element}` : element
                      ).join(", ")}
                    </span>
                  )}
                </div>
              </div>
            ) : (
              <>
                {currentQuestion.inconsistency.inconsistency_parts.map((part, index) => (
                  <div key={index} className="border rounded-lg p-4">
                    {part.type === "text" && (
                      <div>
                        <div className="text-sm text-muted-foreground mb-2">
                          Text from page {part.page}, line {part.line}
                        </div>
                        <p className="italic">"{part.content}"</p>
                      </div>
                    )}
                    {part.type === "image" && (
                      <div>
                        {/* <div className="text-sm text-muted-foreground mb-2">Figure from page {part.page}</div> */}
                        <div className="bg-muted rounded-lg p-4">
                          <Image
                            src={`/images/${part.image_id}.png`}
                            alt={`Image ${part.image_id}`}
                            width={600}
                            height={400}
                            className="max-w-full h-auto rounded-lg"
                            onError={(e) => {
                              const target = e.target as HTMLImageElement
                              target.style.display = "none"
                              const fallback = target.nextElementSibling as HTMLElement
                              if (fallback) fallback.style.display = "block"
                            }}
                          />
                          <div className="text-center text-muted-foreground py-8 hidden">
                            <p>[Image: {part.image_id}]</p>
                            <p className="text-xs mt-2">Image not found</p>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Question</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="mb-6">{currentQuestion.question}</p>

            <RadioGroup value={selectedAnswer} onValueChange={setSelectedAnswer}>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {currentQuestion.options.map((option, index) => (
                  <div
                    key={index}
                    className="flex items-center space-x-2 p-4 rounded-lg hover:bg-muted/50 border border-transparent hover:border-border transition-colors"
                  >
                    <RadioGroupItem value={option} id={`option-${index}`} />
                    <Label htmlFor={`option-${index}`} className="flex-1 cursor-pointer leading-relaxed">
                      {(() => {
                        try {
                          const parsed = JSON.parse(option);
                          return <pre className="whitespace-pre-wrap text">{JSON.stringify(parsed, null, 2)}</pre>;
                        } catch {
                          return option;
                        }
                      })()}
                    </Label>
                  </div>
                ))}
              </div>
            </RadioGroup>

            <Button
              onClick={handleNextQuestion}
              disabled={!selectedAnswer || isSubmitting}
              className="w-full mt-6 cursor-pointer"
              size="lg"
            >
              {isSubmitting ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  Submitting...
                </>
              ) : currentQuestionIndex < questions.length - 1 ? (
                "Next Question"
              ) : (
                "Complete Survey"
              )}
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
