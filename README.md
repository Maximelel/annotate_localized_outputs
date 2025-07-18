# LLM Output Annotation Tool

A web-based tool for annotating Large Language Model (LLM) outputs with a WhatsApp-style interface. Built with FastAPI and Tailwind CSS, this tool provides an intuitive way to evaluate LLM responses across multiple criteria.

## 🚀 Features

### Core Functionality
- **WhatsApp-style Interface**: Clean, familiar chat-like display for user questions and LLM responses
- **Multi-criteria Annotation**: Rate responses on four key dimensions, each with three options
- **Progress Tracking**: Real-time progress bar and completion statistics
- **Skip Functionality**: Skip items and return to them later without affecting progress
- **Flexible Navigation**: Move between items with Previous/Next buttons

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
   ```
   ```bash
   cd annotate_localized_outputs
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Access the application**:
   Open your browser and go to `http://localhost:8000`

## 🆚 Single vs. Pairwise Evaluation Modes

This tool supports two modes for evaluating LLM outputs:

### 1. Single LLM Evaluation (`main_single.py`)
- **Purpose:** Evaluate the output of one LLM at a time.
- **How to run:**
  ```bash
  uvicorn main_single:app --reload
  ```
- **CSV Format:**
  - `UserQuestion`: The user's input/question
  - `ModelAnswer`: The LLM's response
- **UI:**
  - For each question, you see the user question and the LLM's answer.
  - You rate the answer on four criteria (Contextual Relevance, Pedagogical Quality, Actionability, Communication Style), each with three options.

### 2. Pairwise LLM Evaluation (`main_pairs.py`)
- **Purpose:** Compare the outputs of two LLMs side by side for each question.
- **How to run:**
  ```bash
  uvicorn main_pairs:app --reload
  ```
- **CSV Format:**
  - `UserQuestion`: The user's input/question
  - `ModelAnswer1`: The first LLM's response
  - `ModelAnswer2`: The second LLM's response
- **UI:**
  - For each question, you see the user question and both LLMs' answers in two columns.
  - For each of the four criteria, you select which LLM performed better (LLM 1 or LLM 2).
  - You can also leave a comment for each question.

Choose the mode that matches your evaluation needs!



## 🎯 Annotation Criteria

- **Contextual Relevance**: How well does the response fit the user's context? (Excellent, Good, Poor)
- **Pedagogical Quality**: Is the response educationally sound? (Effective, Acceptable, Ineffective)
- **Actionability**: Are the suggestions practical and actionable? (Very Actionable, Somewhat Actionable, Not Actionable)
- **Communication Style**: Is the tone appropriate? (Supportive & Encouraging, Neutral & Factual, Condescending or Dismissive)

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
- Annotation columns: `ContextualRelevance_rating`, `PedagogicalQuality_rating`, `Actionability_rating`, `CommunicationStyle_rating`, `Comments`

**Happy Annotation! 🎉** 
