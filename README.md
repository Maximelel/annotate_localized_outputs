# LLM Output Annotation Tool

A web-based tool for annotating Large Language Model (LLM) outputs with a WhatsApp-style interface. Built with FastAPI and Tailwind CSS, this tool provides an intuitive way to evaluate LLM responses across multiple criteria.

## 🚀 Features

### Core Functionality
- **WhatsApp-style Interface**: Clean, familiar chat-like display for user questions and LLM responses
- **Multi-criteria Annotation**: Rate responses on key dimensions:
- **Progress Tracking**: Real-time progress bar and completion statistics
- **Skip Functionality**: Skip items and return to them later without affecting progress
- **Flexible Navigation**: Move between items with Previous/Next buttons

### Technical Features
- **Single-file Application**: All backend logic, HTML, and JavaScript in one file
- **In-memory State Management**: Global session state for seamless navigation
- **CSV Import/Export**: Easy data import and annotated results export
- **Real-time Validation**: Form validation and button state management
- **Error Handling**: Comprehensive error messages and validation

## 📋 Requirements

- Python 3.7+
- FastAPI
- Uvicorn
- Pandas
- Python-multipart

## 🛠️ Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/Maximelel/annotate_localized_outputs.git
   cd annotate_localized_outputs
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**:
   ```bash
   uvicorn main:app --reload
   ```

4. **Access the application**:
   Open your browser and go to `http://localhost:8000`

## 📖 Usage Guide

### 1. Prepare Your Data
Your CSV file must contain exactly these two columns:
- `UserQuestion`: The user's input/question
- `ModelAnswer`: The LLM's response

Example CSV format:
```csv
UserQuestion,ModelAnswer
"What is machine learning?","Machine learning is a subset of artificial intelligence..."
"How do I implement a neural network?","To implement a neural network, you need to..."
```

### 2. Upload and Annotate
1. **Upload CSV**: Click "Choose File" and select your CSV file
2. **Navigate**: Use Previous/Next buttons to move between items
3. **Rate Responses**: Click Good/Neutral/Bad for each criterion
4. **Add Comments**: Optional text comments for each criterion
5. **Skip Items**: Use the Skip button to return to items later
6. **Track Progress**: Monitor completion percentage and skipped items

### 3. Save Results
1. **Finish Annotation**: Click "Finish and Save" when done
2. **Choose Action**: Select "Save" or "Quit without saving"
3. **Enter Filename**: Provide a custom filename (required)
4. **Download**: File will automatically download as CSV
5. **Restart**: Click "Start New Annotation" to begin a new session

## 🎯 Annotation Criteria

### [TODO]

## 📊 Progress Tracking

The tool provides comprehensive progress tracking:
- **Progress Bar**: Visual completion percentage
- **Annotation Count**: "Annotated X of Y" with percentage
- **Skip Counter**: Number of skipped items in yellow
- **Question Index**: Current question number being annotated
- **Real-time Updates**: Progress updates as you annotate

## 🔧 Technical Architecture

### Single-File Design
All application logic is contained in `main.py`:
- FastAPI backend with HTML generation via f-strings
- Tailwind CSS for styling (loaded from CDN)
- Vanilla JavaScript for client-side interactions
- In-memory session state management

### Key Endpoints
- `GET /`: Upload page or redirect to annotation
- `POST /upload`: CSV file upload and validation
- `GET /annotate`: Main annotation interface
- `POST /api/annotate`: Save annotation data
- `POST /api/navigate`: Navigate between items
- `POST /save-file`: Download annotated results
- `GET /restart`: Clear session and return to upload

### State Management
Global `session_state` dictionary tracks:
- `data_rows`: Original CSV data
- `annotations`: Collected annotation data
- `current_index`: Current item being annotated
- `total_rows`: Total number of items
- `file_saved`: Save status flag

## 🚨 Error Handling

The application includes comprehensive error handling:
- **CSV Validation**: Checks for required columns and data
- **File Format**: Validates CSV structure and encoding
- **Session Management**: Handles missing or corrupted session data
- **User Feedback**: Clear error messages with actionable guidance

## 🔄 Workflow

1. **Upload**: Select and validate CSV file
2. **Annotate**: Rate responses on three criteria
3. **Navigate**: Move between items with Previous/Next
4. **Skip**: Mark items for later review
5. **Save**: Download annotated results as CSV
6. **Restart**: Begin new annotation session

## 📝 Output Format

The exported CSV includes:
- Original columns: `UserQuestion`, `ModelAnswer`
- Annotation columns: `Localization_rating`, `Localization_comment`, `Pedagogy_rating`, `Pedagogy_comment`, `Helpfulness_rating`, `Helpfulness_comment`


**Happy Annotation! 🎉** 
