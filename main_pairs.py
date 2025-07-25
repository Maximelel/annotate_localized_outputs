import uvicorn
from fastapi import FastAPI, Request, Form, UploadFile, File, Response
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import io
import json

app = FastAPI()

# --- Configuration ---
# Define the criteria for pairwise comparison on the left side of the UI.
# Format: (InternalKey, DisplayLabel, Description)
PAIRWISE_CRITERIA = [
    ('ContextualRelevance', 'Contextual Relevance', 'How well does the answer fit the local educational environment?'),
    ('PedagogicalQuality', 'Pedagogical Quality', 'How effective is the teaching advice?'),
    ('CommunicationStyle', 'Communication Style', 'How does the chatbot communicate (Tone, Persona)?'),
    ('FollowupQuality', 'Follow-up Quality', 'How good is the follow-up question(s) for the specific query?'),
    ('OverallQuality', 'Overall Quality🏆', 'Which answer would you like to receive?')
]
# Get a list of the internal keys for validation purposes.
REQUIRED_CRITERIA_KEYS = [key for key, _, _ in PAIRWISE_CRITERIA]

# Define the common issues for the right side of the UI.
# Format: (InternalKey, DisplayLabel)
COMMON_ISSUES = [
    ('Too_Wordy', 'Too Wordy (answer should be more concise)'),
    ('No_Answer', 'No answer but should have been answered'),
    ('Should_Not_Answer', 'Answer but should NOT have been answered')
]

# --- Global Session State ---
def get_default_state():
    return {
        'data_rows': [],
        'annotations': [],
        'current_index': 0,
        'total_rows': 0,
        'columns': [],
        'filename': None,
    }
session_state = get_default_state()

# --- HTML Rendering Helpers ---

def render_upload_page(error=None):
    # Renders the initial file upload page.
    return f"""
    <!DOCTYPE html>
    <html lang='en'>
    <head>
        <meta charset='UTF-8'>
        <meta name='viewport' content='width=device-width, initial-scale=1.0'>
        <title>LLM Output Annotation</title>
        <script src='https://cdn.tailwindcss.com'></script>
    </head>
    <body class='bg-gray-100 min-h-screen flex items-center justify-center'>
        <div class='bg-white shadow-lg rounded-lg p-8 w-full max-w-md'>
            <h1 class='text-2xl font-bold mb-4 text-center'>LLM Output Annotation</h1>
            {f"<div class='mb-4 text-red-500 text-center'>{error}</div>" if error else ''}
            <form action='/upload' method='post' enctype='multipart/form-data' class='flex flex-col gap-4'>
                <label class='block text-gray-700'>Upload CSV file</label>
                <input type='file' name='file' accept='.csv' required class='border rounded p-2'>
                <button type='submit' class='bg-green-500 text-white rounded p-2 hover:bg-green-600'>Upload</button>
            </form>
        </div>
    </body>
    </html>
    """

def render_annotation_page():
    # Renders the main annotation interface.
    idx = session_state['current_index']
    total = session_state['total_rows']
    data = session_state['data_rows'][idx] if total > 0 else {}
    annotations = session_state['annotations']
    prev_ann = annotations[idx] if idx < len(annotations) else {}
    
    def get_choice(crit):
        return prev_ann.get(f'{crit}_winner', '')
    
    def get_comment():
        return prev_ann.get('Comments', '')
        
    def get_issue_checked(llm, issue):
        return 'checked' if prev_ann.get(f'LLM_{llm}_{issue}', False) else ''

    # Calculate progress based on completed annotations.
    completed_count = sum(1 for ann in session_state['annotations'] if all(ann.get(f'{key}_winner') for key in REQUIRED_CRITERIA_KEYS))
    skipped_count = sum(1 for ann in session_state['annotations'] if not all(ann.get(f'{key}_winner') for key in REQUIRED_CRITERIA_KEYS) and any(ann))
    progress_percentage = (completed_count / total * 100) if total > 0 else 0
    
    return f"""
    <!DOCTYPE html>
    <html lang='en'>
    <head>
        <meta charset='UTF-8'>
        <meta name='viewport' content='width=device-width, initial-scale=1.0'>
        <title>Annotate LLM Outputs</title>
        <script src='https://cdn.tailwindcss.com'></script>
    </head>
    <body class='bg-gray-100 min-h-screen flex flex-col items-center'>
        <div class='w-full max-w-7xl mt-8'>
            <div class='mb-6'>
                <div class='flex justify-between items-center mb-2'>
                    <div class='text-gray-600 text-sm'>Annotated {completed_count} of {total} ({progress_percentage:.1f}% done)</div>
                    <div class='text-yellow-600 text-sm font-medium'>Skipped: {skipped_count}</div>
                </div>
                <div class='w-full bg-gray-200 rounded-full h-2'>
                    <div class='bg-green-500 h-2 rounded-full transition-all duration-300' style='width: {progress_percentage}%'></div>
                </div>
                <div class='text-left mt-2'>
                    <span class='text-gray-800 text-lg font-bold'>Question #{idx + 1}</span>
                </div>
            </div>
            <div class='bg-white rounded-lg shadow p-6 mb-6'>
                <div class='mb-4'>
                    <div class='font-semibold mb-2'>User{f" ({data.get('AssignedCountry', '').upper()})" if data.get('AssignedCountry', '').strip() else ''}:</div>
                    <div class='bg-gray-200 text-gray-800 rounded-2xl px-4 py-2 max-w-[98%] mb-4'>{data.get('UserQuestion', '').replace(chr(10), '<br>').replace(chr(13), '<br>')}</div>
                    <div class='grid grid-cols-2 gap-6'>
                        <div class='flex flex-col'>
                            <div class='font-semibold mb-1 text-center'>LLM 1</div>
                            <div class='bg-green-100 text-green-900 rounded-2xl px-6 py-2 min-h-[40px] max-w-[95%]'>{data.get('ModelAnswer1', '').replace(chr(10), '<br>').replace(chr(13), '<br>')}</div>
                        </div>
                        <div class='flex flex-col'>
                            <div class='font-semibold mb-1 text-center'>LLM 2</div>
                            <div class='bg-blue-100 text-blue-900 rounded-2xl px-6 py-2 min-h-[40px] max-w-[95%]'>{data.get('ModelAnswer2', '').replace(chr(10), '<br>').replace(chr(13), '<br>')}</div>
                        </div>
                    </div>
                </div>
            </div>
            <form id='annotationForm' class='bg-white rounded-lg shadow p-6 flex flex-col gap-6'>
                <input type='hidden' name='index' id='index' value='{idx}'>
                <div class='grid grid-cols-1 md:grid-cols-3 gap-x-8 gap-y-6'>
                    <div class='md:col-span-2'>
                        {render_pairwise_rubric(get_choice)}
                    </div>
                    <div class='md:col-span-1'>
                        {render_common_issues_rubric(get_issue_checked)}
                    </div>
                </div>
                <div class='border-t pt-6'>
                    <label for='Comments' class='block font-semibold mb-1'>Comments <span class='text-gray-500 text-xs'>(optional)</span></label>
                    <textarea id='Comments' name='Comments' class='border rounded p-2 w-full text-sm' rows='2' placeholder='Add any comments here...'>{get_comment()}</textarea>
                </div>
                <div class='flex justify-between items-center mt-4'>
                    {render_previous_button(idx)}
                    <div class='flex gap-2'>
                        <button type='button' onclick='skipAnnotation()' class='bg-yellow-500 text-white px-4 py-2 rounded hover:bg-yellow-600'>Skip</button>
                        <button type='button' onclick='submitAnnotation()' id='nextButton' class='bg-green-500 text-white px-4 py-2 rounded hover:bg-green-600 opacity-50 cursor-not-allowed' disabled>Next</button>
                    </div>
                    <button type='button' onclick='showFinishConfirm()' class='bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600'>Finish and Save</button>
                </div>
            </form>
            <div id="finishConfirmModal" class="fixed inset-0 bg-black bg-opacity-40 flex items-center justify-center z-50 hidden">
                <div class="bg-white rounded-lg shadow-lg p-8 max-w-sm w-full flex flex-col items-center">
                    <h2 class="text-xl font-bold mb-4 text-center">Are you sure you want to finish and save?</h2>
                    <div class="flex gap-4 mt-2">
                        <button onclick="confirmFinishYes()" class="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600">Yes, Finish</button>
                        <button onclick="confirmFinishNo()" class="bg-gray-300 text-gray-700 px-4 py-2 rounded hover:bg-gray-400">No, Go Back</button>
                    </div>
                </div>
            </div>
        </div>
        
        <script>
            // Store criteria keys from backend for JS validation
            const requiredCriteria = {json.dumps(REQUIRED_CRITERIA_KEYS)};
            const allIssueKeys = {json.dumps([key for key, _ in COMMON_ISSUES])};

            function handlePairwiseClick(criterion, value) {{
                // Logic to handle button clicks for pairwise comparison and update UI
                ['LLM_1', 'LLM_2', 'NO_PREF'].forEach(val => {{
                    document.getElementById(`${{criterion}}_${{val}}`).classList.remove('ring-2', 'ring-green-500', 'ring-blue-500', 'ring-gray-400');
                }});
                const ringColor = value === 'LLM_1' ? 'ring-green-500' : value === 'LLM_2' ? 'ring-blue-500' : 'ring-gray-400';
                document.getElementById(`${{criterion}}_${{value}}`).classList.add('ring-2', ringColor);
                document.getElementById(`${{criterion}}_winner`).value = value;
                checkNextButton();
            }}

            function checkNextButton() {{
                // Enable 'Next' button only when all required criteria are selected
                const allSelected = requiredCriteria.every(crit => document.getElementById(`${{crit}}_winner`).value);
                const nextButton = document.getElementById('nextButton');
                if (allSelected) {{
                    nextButton.disabled = false;
                    nextButton.classList.remove('opacity-50', 'cursor-not-allowed');
                }} else {{
                    nextButton.disabled = true;
                    nextButton.classList.add('opacity-50', 'cursor-not-allowed');
                }}
            }}
            
            // Run on page load to set initial button state
            document.addEventListener('DOMContentLoaded', checkNextButton);

            function getFormData() {{
                // Helper to gather all form data into a single payload object
                const index = parseInt(document.getElementById('index').value);
                let payload = {{ index: index, Comments: document.getElementById('Comments').value }};
                
                // Get pairwise winners
                requiredCriteria.forEach(crit => {{
                    payload[`${{crit}}_winner`] = document.getElementById(`${{crit}}_winner`).value;
                }});

                // Get common issues for both LLMs
                [1, 2].forEach(llmNum => {{
                    allIssueKeys.forEach(issueKey => {{
                        payload[`LLM_${{llmNum}}_${{issueKey}}`] = document.getElementById(`llm${{llmNum}}_issue_${{issueKey.toLowerCase()}}`).checked;
                    }});
                }});
                return payload;
            }}
            
            async function submitAnnotation() {{
                // Submit the current annotation and move to the next item
                const payload = getFormData();
                await postAnnotation(payload);
                navigate('next');
            }}
            
            async function skipAnnotation() {{
                // Skip the current item by submitting an empty annotation
                const index = parseInt(document.getElementById('index').value);
                let payload = {{ index: index }};
                requiredCriteria.forEach(crit => payload[`${{crit}}_winner`] = '');
                [1, 2].forEach(llmNum => allIssueKeys.forEach(key => payload[`LLM_${{llmNum}}_${{key}}`] = false));
                payload['Comments'] = '';
                await postAnnotation(payload);
                navigate('next');
            }}

            async function confirmFinishYes() {{
                // Save the current annotation and redirect to the finish page
                document.getElementById('finishConfirmModal').classList.add('hidden');
                const payload = getFormData();
                await postAnnotation(payload);
                window.location.href = '/finish';
            }}

            function confirmFinishNo() {{
                // Hide the confirmation modal
                document.getElementById('finishConfirmModal').classList.add('hidden');
            }}
            
            function showFinishConfirm() {{
                // Show the confirmation modal
                document.getElementById('finishConfirmModal').classList.remove('hidden');
            }}

            async function postAnnotation(payload) {{
                // Central function to POST annotation data to the backend
                await fetch('/api/annotate', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify(payload)
                }});
            }}
            
            async function navigate(direction) {{
                // Navigate between previous/next items
                await fetch('/api/navigate', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{direction: direction}})
                }});
                window.location.href = '/annotate';
            }}
        </script>
    </body>
    </html>
    """

def render_pairwise_rubric(get_choice):
    # Renders the left-side criteria using the PAIRWISE_CRITERIA config.
    btns = ["<div class='flex flex-col gap-4'>"]
    for crit, label, expl in PAIRWISE_CRITERIA:
        btns.append(
            f"""
            <div>
                <div class='mb-1 font-semibold'>{label}: <span class='font-normal text-gray-600'>{expl}</span></div>
                <div class='flex items-center gap-4 mb-2'>
                    <input type='hidden' id='{crit}_winner' name='{crit}_winner' value='{get_choice(crit)}'>
                    <button type='button' id='{crit}_LLM_1' onclick="handlePairwiseClick('{crit}','LLM_1')" class='px-4 py-1 rounded border bg-green-50 border-green-300 {'ring-2 ring-green-500' if get_choice(crit)=='LLM_1' else ''}'>LLM 1</button>
                    <button type='button' id='{crit}_LLM_2' onclick="handlePairwiseClick('{crit}','LLM_2')" class='px-4 py-1 rounded border bg-blue-50 border-blue-300 {'ring-2 ring-blue-500' if get_choice(crit)=='LLM_2' else ''}'>LLM 2</button>
                    <button type='button' id='{crit}_NO_PREF' onclick="handlePairwiseClick('{crit}','NO_PREF')" class='px-4 py-1 rounded border bg-gray-100 border-gray-400 text-gray-500 {'ring-2 ring-gray-400' if get_choice(crit)=='NO_PREF' else ''}'>No preference</button>
                </div>
            </div>
            """
        )
    btns.append("</div>")
    return "".join(btns)

def render_common_issues_rubric(get_issue_checked):
    # Renders the right-side common issues using the COMMON_ISSUES config.
    html = ["<div class='flex flex-col gap-6'>"]
    for llm_num in [1, 2]:
        html.append(f"<div><div class='font-semibold mb-2'>LLM {llm_num} common issues <span class='text-gray-500 text-xs'>(optional)</span></div><div class='flex flex-col gap-1'>")
        for issue_key, issue_label in COMMON_ISSUES:
            html.append(
                f"""
                <label class='flex items-center gap-2'>
                    <input type='checkbox' id='llm{llm_num}_issue_{issue_key.lower()}' name='llm{llm_num}_issue_{issue_key.lower()}' class='h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500' {get_issue_checked(llm_num, issue_key)}>
                    <span>{issue_label}</span>
                </label>
                """
            )
        html.append("</div></div>")
    html.append("</div>")
    return "".join(html)

def render_previous_button(idx):
    # Renders the 'Previous' button if not on the first item.
    if idx > 0:
        return '<button type="button" onclick="navigate(\'previous\')" class="bg-gray-300 text-gray-700 px-4 py-2 rounded hover:bg-gray-400">Previous</button>'
    return '<div></div>' # Placeholder for alignment

# Other rendering helpers (finish, save, goodbye pages) remain largely the same.
def render_finish_page():
    return """
    <!DOCTYPE html><html lang='en'><head><meta charset='UTF-8'><title>Finish Annotation</title><script src='https://cdn.tailwindcss.com'></script></head>
    <body class='bg-gray-100 min-h-screen flex items-center justify-center'><div class='bg-white shadow-lg rounded-lg p-8 w-full max-w-md'>
    <h1 class='text-2xl font-bold mb-6 text-center'>Finish Annotation</h1><div class='flex flex-col gap-4'>
    <button onclick="window.location.href='/quit'" class='bg-red-500 text-white rounded p-3 hover:bg-red-600'>Quit without saving</button>
    <button onclick="window.location.href='/save'" class='bg-green-500 text-white rounded p-3 hover:bg-green-600'>Save Annotations</button>
    </div></div></body></html>
    """

def render_save_page():
    return """
    <!DOCTYPE html><html lang='en'><head><meta charset='UTF-8'><title>Save Results</title><script src='https://cdn.tailwindcss.com'></script></head>
    <body class='bg-gray-100 min-h-screen flex items-center justify-center'><div class='bg-white shadow-lg rounded-lg p-8 w-full max-w-md'>
    <h1 class='text-2xl font-bold mb-6 text-center'>Save Results</h1><form action='/save-file' method='post' class='flex flex-col gap-4'>
    <label class='block text-gray-700'>Filename (e.g., my_annotations)</label>
    <input type='text' name='filename' id='filename' required class='border rounded p-2' placeholder='Enter filename...'>
    <button type='submit' id='saveButton' class='bg-gray-400 text-white rounded p-3 cursor-not-allowed' disabled>Save and Download CSV</button>
    </form></div><script>
    document.getElementById('filename').addEventListener('input', function() {
        const btn = document.getElementById('saveButton');
        if (this.value.trim().length > 0) {
            btn.disabled = false;
            btn.classList.remove('bg-gray-400', 'cursor-not-allowed');
            btn.classList.add('bg-blue-500', 'hover:bg-blue-600');
        } else {
            btn.disabled = true;
            btn.classList.add('bg-gray-400', 'cursor-not-allowed');
            btn.classList.remove('bg-blue-500', 'hover:bg-blue-600');
        }
    });
    </script></body></html>
    """

def render_goodbye_page(action="saved"):
    message = "Your annotations have been saved successfully!" if action == "saved" else "You quit without saving. Your annotations have been lost."
    return f"""
    <!DOCTYPE html><html lang='en'><head><meta charset='UTF-8'><title>Goodbye</title><script src='https://cdn.tailwindcss.com'></script></head>
    <body class='bg-gray-100 min-h-screen flex items-center justify-center'><div class='bg-white shadow-lg rounded-lg p-8 w-full max-w-md'>
    <h1 class='text-2xl font-bold mb-6 text-center'>Goodbye!</h1><p class='text-gray-600 mb-6 text-center'>{message}</p>
    <div class='flex justify-center'><button onclick="window.location.href='/restart'" class='bg-blue-500 text-white rounded p-3 hover:bg-blue-600'>Start New Annotation</button></div>
    </div></body></html>
    """

# --- FastAPI Endpoints ---

@app.get("/", response_class=HTMLResponse)
def index():
    # Main entry point. Shows upload page or redirects to annotation.
    if not session_state['data_rows']:
        return render_upload_page()
    return RedirectResponse('/annotate', status_code=302)

@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    # Handles file upload and session initialization.
    content = await file.read()
    try:
        df = pd.read_csv(io.StringIO(content.decode('utf-8')))
    except Exception:
        return HTMLResponse(render_upload_page(error='Invalid CSV file.'), status_code=400)
    
    required_cols = ['UserQuestion', 'ModelAnswer1', 'ModelAnswer2']
    if not all(col in df.columns for col in required_cols):
        error_msg = f'CSV is missing required columns: {", ".join(required_cols)}. Found: {", ".join(df.columns)}'
        return HTMLResponse(render_upload_page(error=error_msg), status_code=400)
    
    session_state['data_rows'] = df.to_dict(orient='records')
    session_state['annotations'] = [{} for _ in range(len(df))]
    session_state['current_index'] = 0
    session_state['total_rows'] = len(df)
    session_state['columns'] = list(df.columns)
    session_state['filename'] = file.filename
    return RedirectResponse('/annotate', status_code=302)

@app.get("/annotate", response_class=HTMLResponse)
def annotate():
    # Displays the main annotation page.
    if not session_state['data_rows']:
        return RedirectResponse('/', status_code=302)
    return render_annotation_page()

@app.post("/api/annotate")
async def api_annotate(request: Request):
    # API endpoint to save a single annotation to the session state.
    data = await request.json()
    idx = data.get('index', 0)
    
    ann = {'Comments': data.get('Comments', '')}
    # Add pairwise winners
    for key in REQUIRED_CRITERIA_KEYS:
        ann[f'{key}_winner'] = data.get(f'{key}_winner', '')
    # Add common issues
    for llm_num in [1, 2]:
        for issue_key, _ in COMMON_ISSUES:
            ann[f'LLM_{llm_num}_{issue_key}'] = data.get(f'LLM_{llm_num}_{issue_key}', False)
            
    if 0 <= idx < len(session_state['annotations']):
        session_state['annotations'][idx] = ann
    
    return {"status": "success"}

@app.post("/api/navigate")
async def api_navigate(request: Request):
    # API endpoint to handle moving between previous/next items.
    data = await request.json()
    direction = data.get('direction')
    if direction == 'next' and session_state['current_index'] < session_state['total_rows'] - 1:
        session_state['current_index'] += 1
    elif direction == 'previous' and session_state['current_index'] > 0:
        session_state['current_index'] -= 1
    return {"status": "success", "index": session_state['current_index']}

@app.get("/finish", response_class=HTMLResponse)
def finish():
    return render_finish_page()

@app.get("/save", response_class=HTMLResponse)
def save():
    return render_save_page()

@app.post("/save-file", response_class=StreamingResponse)
async def save_file(filename: str = Form(...)):
    # Compiles annotations and data into a CSV file for download.
    df = pd.DataFrame(session_state['data_rows'])
    ann_df = pd.DataFrame(session_state['annotations'])
    out_df = pd.concat([df, ann_df], axis=1)
    
    buf = io.StringIO()
    out_df.to_csv(buf, index=False)
    buf.seek(0)
    
    safe_filename = "".join(c for c in filename if c.isalnum() or c in (' ', '_')).rstrip()
    return StreamingResponse(iter([buf.getvalue()]), media_type='text/csv', headers={
        'Content-Disposition': f'attachment; filename="{safe_filename}.csv"'
    })

@app.get("/restart")
def restart():
    # Clears the session and restarts the application.
    global session_state
    session_state = get_default_state()
    return RedirectResponse('/', status_code=302)

@app.get("/quit")
def quit():
    # Quits the session and shows a goodbye message.
    global session_state
    session_state = get_default_state()
    return render_goodbye_page(action="quit")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)