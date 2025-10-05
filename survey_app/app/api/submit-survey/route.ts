import { type NextRequest, NextResponse } from "next/server"
import { google } from "googleapis"

interface SurveyResult {
  inconsistency_id: string
  inconsistency_index: number
  question: string
  correct_answer: string
  user_answer: string
  is_correct: boolean
  is_pdf_question: boolean
  answer_time_ms: number
  user_info: {
    email: string
    academicField: string
    academicLevel: string
    aiExposure: string
  }
}

export async function POST(request: NextRequest) {
  try {
    const data: SurveyResult[] = await request.json()

    // Initialize Google Sheets API
    const auth = new google.auth.GoogleAuth({
      credentials: {
        client_email: process.env.GOOGLE_SHEETS_CLIENT_EMAIL,
        private_key: process.env.GOOGLE_SHEETS_PRIVATE_KEY?.replace(/\\n/g, "\n"),
      },
      scopes: ["https://www.googleapis.com/auth/spreadsheets"],
    })

    const sheets = google.sheets({ version: "v4", auth })
    const spreadsheetId = process.env.GOOGLE_SHEETS_SPREADSHEET_ID

    if (!spreadsheetId) {
      throw new Error("Google Sheets Spreadsheet ID not configured")
    }

    // Prepare data for Google Sheets
    const timestamp = new Date().toISOString()
    const rows = data.map((result) => [
      timestamp,
      result.user_info.email,
      result.user_info.academicField,
      result.user_info.academicLevel,
      result.user_info.aiExposure,
      result.inconsistency_id,
      result.inconsistency_index,
      result.question,
      result.correct_answer,
      result.user_answer,
      result.is_correct ? "TRUE" : "FALSE",
      result.is_pdf_question ? "TRUE" : "FALSE",
      Math.round(result.answer_time_ms / 1000), // Answer time in seconds (rounded)
    ])

    // Check if headers exist, if not create them
    try {
      const headerResponse = await sheets.spreadsheets.values.get({
        spreadsheetId,
        range: "Sheet1!A1:N1",
      })

      if (!headerResponse.data.values || headerResponse.data.values.length === 0) {
        // Add headers
        await sheets.spreadsheets.values.update({
          spreadsheetId,
          range: "Sheet1!A1:N1",
          valueInputOption: "RAW",
          requestBody: {
            values: [
              [
                "Timestamp",
                "Email",
                "Academic Field",
                "Academic Level",
                "AI Exposure",
                "Inconsistency ID",
                "Inconsistency Index",
                "Question",
                "Correct Answer",
                "User Answer",
                "Is Correct",
                "Is PDF Question",
                "Answer Time (seconds)",
              ],
            ],
          },
        })
      }
    } catch (error) {
      console.error("Error checking/creating headers:", error)
    }

    // Append the survey results
    await sheets.spreadsheets.values.append({
      spreadsheetId,
      range: "Sheet1!A:N",
      valueInputOption: "RAW",
      insertDataOption: "INSERT_ROWS",
      requestBody: {
        values: rows,
      },
    })

    return NextResponse.json({ success: true, message: "Survey results saved successfully" })
  } catch (error) {
    console.error("Error saving survey results:", error)
    return NextResponse.json({ success: false, error: "Failed to save survey results" }, { status: 500 })
  }
}
