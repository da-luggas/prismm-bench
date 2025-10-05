import { NextRequest, NextResponse } from "next/server"
import { google } from "googleapis"

export async function POST(request: NextRequest) {
  try {
    const { email } = await request.json()
    if (!email) {
      return NextResponse.json({ error: "Email is required" }, { status: 400 })
    }

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

    // Fetch all rows for this email
    const response = await sheets.spreadsheets.values.get({
      spreadsheetId,
      range: "Sheet1!A:N",
    })
    const rows = response.data.values || []
    // Email is in column 2 (index 1), Inconsistency ID is in column 6 (index 5)
    const answeredIds = rows
      .filter((row) => row[1] === email)
      .map((row) => row[5])
      .filter(Boolean)

    return NextResponse.json({ answeredIds })
  } catch (error) {
    console.error("Error fetching answered inconsistencies:", error)
    return NextResponse.json({ error: "Failed to fetch answered inconsistencies" }, { status: 500 })
  }
}
