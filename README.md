# LLM Pairwise Evaluation Tool

This repository contains a web-based tool for the pairwise comparison of Large Language Model (LLM) outputs. Built with **FastAPI** and **Tailwind CSS**, this application provides an intuitive, chat-style interface to efficiently evaluate two LLM responses side-by-side against a defined set of criteria.

The tool is designed for researchers, developers, and data annotators who need to systematically compare the performance of two different models, or two versions of the same model, on a given set of prompts.

***

## 🚀 Core Features

* **WhatsApp-style Interface**: Displays answers from two LLMs in a clean, two-column layout for easy comparison.
* **Multi-Criteria Rubric**: Evaluate model performance across five distinct criteria, choosing which model was better or if there was no preference.
* **Common Issue Flagging**: Quickly tag common problems in each model's response, such as being too wordy or failing to answer.
* **Progress Tracking**: A visual progress bar shows how many items have been completed, and a counter tracks skipped items.
* **Simple Data Handling**: Upload a CSV file to start and download your work as a new, annotated CSV upon completion.
* **Easy Navigation**: Move forward and backward through your dataset with "Next" and "Previous" buttons.

***

## 🛠️ Installation and Usage

Follow these steps to get the annotation tool running on your local machine.

### 1. Requirements

Make sure you have Python 3.7+ installed. The required Python libraries are:
* `fastapi`
* `uvicorn`
* `pandas`
* `python-multipart`

### 2. Setup

First, clone the repository to your local machine:
```bash
git clone https://github.com/Maximelel/annotate_localized_outputs.git
```
```bash
cd annotate_localized_outputs
```

Next, install the required dependencies. It's recommended to do this in a virtual environment.

```bash
pip install -r requirements.txt
```

### 3\. Running the Application

To start the web server, run the following command from the root directory of the project:

```bash
uvicorn main_pairs:app --reload
```
-----

## 📖 How to Use the Tool

### 1\. Prepare Your Data

Your input data must be a **CSV file** containing the following three columns:

  * `UserQuestion`: The prompt or question given to the LLMs.
  * `ModelAnswer1`: The full response from the first LLM.
  * `ModelAnswer2`: The full response from the second LLM.

*Optional columns like `AssignedCountry` can be included and will be displayed in the UI if present.*

### 2\. Upload and Annotate

1.  **Upload**: On the main page, you'll be prompted to upload your CSV file.
2.  **Annotate**: Once uploaded, the annotation interface will appear.
      * The **user's question** is displayed at the top.
      * **LLM 1's answer** is on the left (green), and **LLM 2's answer** is on the right (blue).
      * Use the **Pairwise Comparison** rubric on the left to select which model performed better for each criterion (`LLM 1`, `LLM 2`, or `No preference`).
      * The **"Next"** button will only become active after all five criteria have been selected.
3.  **Flag Issues**: On the right, you can optionally check boxes to flag common issues for each LLM.
4.  **Add Comments**: A text box is available at the bottom for any additional notes.

### 3\. Annotation Criteria

You will evaluate the models based on the following five criteria:

1.  **Contextual Relevance**: How well does the answer fit the local educational environment?
2.  **Pedagogical Quality**: How effective is the teaching advice?
3.  **Communication Style**: How does the chatbot communicate (Tone, Persona)?
4.  **Follow-up Quality**: How good is the follow-up question(s) for the specific query?
5.  **Overall Quality 🏆**: Which answer would you prefer to receive?

### 4\. Saving Your Work

When you are finished, click the **"Finish and Save"** button. You will be asked to provide a filename, and your browser will download the complete, annotated dataset as a new CSV file. The output file will contain all the original columns from your input file, plus new columns for each annotation decision, flagged issue, and your comments.
