# Research Survey App

A web application for conducting surveys on human performance in identifying inconsistencies in academic papers.

## Features

- **Welcome Page**: Collects user information (email, academic background, AI exposure)
- **Survey Interface**: Presents randomized questions with multiple choice answers
- **Configurable Question Types**: Support for different question formats via environment variables
- **Google Sheets Integration**: Automatically saves survey results to Google Sheets
- **Progress Tracking**: Shows survey progress and completion status

## Setup Instructions

### 1. Environment Variables

Create a `.env.local` file in the root directory with the following variables:

```env
# Question Type Configuration (optional, defaults to "default")

NEXT_PUBLIC_QUESTION_TYPE=default

# Google Sheets Integration (required for data persistence)

GOOGLE_SHEETS_CLIENT_EMAIL=your-service-account@your-project.iam.gserviceaccount.com
GOOGLE_SHEETS_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\nYour private key here\n-----END PRIVATE KEY-----\n"
GOOGLE_SHEETS_SPREADSHEET_ID=your-spreadsheet-id-here
```

### 2. Google Sheets Setup

1. **Create a Google Cloud Project**:

   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select an existing one

2. **Enable Google Sheets API**:

   - Navigate to "APIs & Services" > "Library"
   - Search for "Google Sheets API" and enable it

3. **Create Service Account**:

   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "Service Account"
   - Fill in the details and create the account

4. **Generate Private Key**:

   - Click on the created service account
   - Go to "Keys" tab > "Add Key" > "Create New Key"
   - Choose JSON format and download the file
   - Extract `client_email` and `private_key` for your environment variables

5. **Create Google Sheet**:
   - Create a new Google Sheet
   - Copy the spreadsheet ID from the URL (the long string between `/d/` and `/edit`)
   - Share the sheet with your service account email (give Editor permissions)

### 3. Question Types

Configure the survey behavior using the `NEXT_PUBLIC_QUESTION_TYPE` environment variable:

- `default`: General inconsistency identification questions
- `default_natural`: General inconsistency in natural language
- `edit`: Questions about how to resolve inconsistencies

### 4. Data Structure

The app expects annotation data in `data/annotations.json` with the following structure:

```json
{
"paper_id": [
{
"inconsistency_parts": [
{
"type": "text|image",
"page": 5,
"content": "text content",
"line": 236,
"image_id": "image_identifier"
}
],
"review_text": "Description of the inconsistency",
"category": "figure-text",
"mcq": {
"default": {
"question": "What is the inconsistency?",
"correct": "Correct answer",
"incorrect": ["Wrong answer 1", "Wrong answer 2", "Wrong answer 3"]
}
}
}
]
}
```

### 5. Image Assets

Place corresponding images in a `public/images/` directory with filenames matching the `image_id` values from your annotations (e.g., `image_id.png`).

## Development

```bash
# Install dependencies

npm install

# Run development server

npm run dev

# Build for production

npm run build
npm start
```

## Data Collection

Survey results are automatically saved to your configured Google Sheet with the following columns:

- Timestamp
- Email
- Academic Background
- AI Exposure
- Inconsistency ID
- Inconsistency Index
- Question
- Correct Answer
- User Answer
- Is Correct (Text)
- Is Correct (Number)

## Configuration Options

Modify `lib/survey-config.ts` to adjust:

- Number of questions per survey (default: 5)
- Option shuffling behavior
- Question randomization
- Available question types
