# Paper Inconsistency Annotation Tool

A web-based application for annotating visual and textual inconsistencies in scientific papers. This tool helps researchers identify and document discrepancies between different parts of academic papers, such as conflicts between tables and text, images and captions, or data visualizations and methodology descriptions.

## Features

- **PDF Viewer Integration**: View scientific papers directly in the browser
- **Dual Annotation Types**: Support for both image and text inconsistencies
- **Image Cropping**: Select specific regions of PDF pages for visual inconsistencies
- **Progress Tracking**: Real-time progress monitoring with save/resume functionality
- **Auto-save**: Automatic progress saving to prevent data loss
- **Export Results**: Download annotated data in JSON format
- **Responsive Design**: Works on desktop and mobile devices

## Installation

### Prerequisites
- Node.js 18+ and npm
- Python 3.8+
- pip (Python package manager)

### Frontend Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd paper-annotation-app
```

2. Install Node.js dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm run dev
```

The frontend will be available at `http://localhost:3000`

### Backend Setup

1. Navigate to the API directory:
```bash
cd app/api
```

2. Install Python dependencies:
```bash
pip install fastapi uvicorn PyMuPDF httpx python-multipart
```

3. Start the FastAPI server:
```bash
uvicorn main:app --host 0.0.0.0 --port 8080 --reload
```

The API will be available at `http://localhost:8080`

## Usage

### 1. Prepare Input Data

Create a JSON file with the following structure:

```json
{
  "paper_id_1": [
    {
      "type": "table-text",
      "description": "Table 1 shows different values than mentioned in the text"
    },
    {
      "type": "image-caption",
      "description": "Figure 2 caption doesn't match the actual image content"
    }
  ],
  "paper_id_2": [
    {
      "type": "data-visualization",
      "description": "Chart values don't align with methodology description"
    }
  ]
}
```

### 2. Start Annotation

1. Open the application in your browser
2. Upload your inconsistency data JSON file
3. Optionally upload a previous progress file to resume work
4. Begin annotating inconsistencies

### 3. Annotation Process

For each inconsistency:

1. **Select Type**: Choose between image or text inconsistency
2. **Specify Page**: Enter the page number where the inconsistency occurs
3. **Image Mode**: 
   - Load the page image
   - Use the cropping tool to select the inconsistent region
   - The tool will automatically extract the cropped area
4. **Text Mode**:
   - Paste the inconsistent text content
   - Specify the line number
5. **Add Metadata**:
   - Select inconsistency category
   - Provide a description
6. **Save**: Click "Save Annotation & Continue"

### 4. Export Results

The tool automatically saves progress locally. You can export the final results as a JSON file containing all annotations with the following structure:

```json
{
  "paper_id": [
    {
      "inconsistency_parts": [
        {
          "type": "image",
          "base64": "data:image/png;base64,...",
          "page": 3,
          "bbox": {
            "x": 0.1,
            "y": 0.2,
            "width": 0.3,
            "height": 0.4
          }
        }
      ],
      "review_text": "Original inconsistency description",
      "category": "table-text",
      "description": "User-provided description"
    }
  ]
}
```

## API Endpoints

### GET `/api/pdf-proxy`
Fetches and serves PDF files from OpenReview.

**Parameters:**
- `paper_id`: The OpenReview paper ID

**Response:** PDF file stream

### GET `/api/pdf-to-image`
Converts a specific PDF page to an image.

**Parameters:**
- `paper_id`: The OpenReview paper ID
- `page`: Page number (1-based)

**Response:** PNG image stream

### GET `/api/remove-paper`
Removes cached PDF files for a specific paper.

**Parameters:**
- `paper_id`: The OpenReview paper ID

**Response:** Success/error message

## Configuration

### Environment Variables

The application supports the following environment variables:

- `NEXT_PUBLIC_API_URL`: Backend API URL (default: `http://localhost:8080`)

### PDF Processing

The backend automatically downloads and caches PDF files from OpenReview. Cached files are stored in the system's temporary directory under `openreview_pdfs/`.


