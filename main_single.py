import uvicorn
from fastapi import FastAPI, Request, Form, UploadFile, File, Response
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import io
import json

app = FastAPI()

# Global session state
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

# Helper: Render upload page
def render_upload_page(error=None):
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

# Helper: Render annotation page
def render_annotation_page():
    idx = session_state['current_index']
    total = session_state['total_rows']
    data = session_state['data_rows'][idx] if total > 0 else {'UserQuestion': '', 'ModelAnswer': ''}
    annotations = session_state['annotations']
    prev_ann = annotations[idx] if idx < len(annotations) else {}
    def get_rating(crit):
        return prev_ann.get(crit + '_rating', '')
    def get_comment():
        return prev_ann.get('Comments', '')
    # Calculate progress - count only completed annotations (not skipped)
    completed_count = sum(1 for ann in session_state['annotations'] if any(ann.get(f'{crit}_rating') for crit in ['ContextualRelevance', 'PedagogicalQuality', 'Actionability', 'CommunicationStyle']))
    skipped_count = sum(1 for ann in session_state['annotations'] if not any(ann.get(f'{crit}_rating') for crit in ['ContextualRelevance', 'PedagogicalQuality', 'Actionability', 'CommunicationStyle']) and any(ann))
    progress_percentage = (completed_count / total * 100) if total > 0 else 0
    remaining = total - completed_count
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
                <div class='flex flex-col gap-4'>
                    <div class='flex'>
                        <div class='bg-gray-200 text-gray-800 rounded-2xl px-4 py-2 max-w-[98%]'>
                            <span class='font-semibold'>User:</span> {data.get('UserQuestion', '').replace(chr(10), '<br>').replace(chr(13), '<br>')}
                        </div>
                    </div>
                    <div class='flex justify-end'>
                        <div class='bg-green-100 text-green-900 rounded-2xl px-4 py-2 max-w-[98%]'>
                            <span class='font-semibold'>LLM:</span> {data.get('ModelAnswer', '').replace(chr(10), '<br>').replace(chr(13), '<br>')}
                        </div>
                    </div>
                </div>
            </div>
            <form id='annotationForm' class='bg-white rounded-lg shadow p-6 flex flex-col gap-6'>
                <input type='hidden' name='index' id='index' value='{idx}'>
                {render_rubric(get_rating)}
                <div class='mb-4'>
                    <label for='Comments' class='block font-semibold mb-1'>Comments <span class='text-gray-500 text-xs'>(optional)</span></label>
                    <textarea id='Comments' name='Comments' class='border rounded p-2 w-full text-sm' rows='2' placeholder='Add any comments here (optional)'>{get_comment()}</textarea>
                </div>
                <div class='flex justify-between items-center mt-4'>
                    {render_previous_button(idx)}
                    <div class='flex gap-2'>
                        <button type='button' onclick='skipAnnotation()' class='bg-yellow-500 text-white px-4 py-2 rounded hover:bg-yellow-600'>Skip</button>
                        <button type='button' onclick='submitAnnotation()' id='nextButton' class='bg-green-500 text-white px-4 py-2 rounded hover:bg-green-600' disabled>Next</button>
                    </div>
                    <button type='button' onclick='showFinishConfirm()' class='bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600'>Finish and Save</button>
                </div>
            </form>
            <!-- Modal for Finish Confirmation -->
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
        let ratings = {{}}
        function handleRatingClick(criterion, value) {{
            ratings[criterion] = value;
            let options = ratingOptions[criterion];
            for (let i = 0; i < options.length; i++) {{
                let v = options[i];
                let btn = document.getElementById(criterion + '_' + v);
                if (btn) btn.classList.remove('ring-2','ring-green-500','ring-gray-400','ring-red-500','text-green-800','text-gray-700','text-red-600');
            }}
            // Add correct ring and font color to selected
            let selectedIdx = ratingOptions[criterion].indexOf(value);
            let btn = document.getElementById(criterion + '_' + value);
            if (btn) {{
                if (selectedIdx === 0) {{
                    btn.classList.add('ring-2','ring-green-500','text-green-800');
                }} else if (selectedIdx === 1) {{
                    btn.classList.add('ring-2','ring-gray-400','text-gray-700');
                }} else if (selectedIdx === 2) {{
                    btn.classList.add('ring-2','ring-red-500','text-red-600');
                }}
            }}
            document.getElementById(criterion + '_rating').value = value;
            checkNextButton();
        }}
        const ratingOptions = {{
            'ContextualRelevance': ['Excellent','Good','Poor'],
            'PedagogicalQuality': ['Effective','Acceptable','Ineffective'],
            'Actionability': ['VeryActionable','SomewhatActionable','NotActionable'],
            'CommunicationStyle': ['Supportive','Neutral','Condescending']
        }};
        function checkNextButton() {{
            const cr = document.getElementById('ContextualRelevance_rating').value;
            const pq = document.getElementById('PedagogicalQuality_rating').value;
            const ac = document.getElementById('Actionability_rating').value;
            const cs = document.getElementById('CommunicationStyle_rating').value;
            const nextButton = document.getElementById('nextButton');
            if (cr && pq && ac && cs) {{
                nextButton.disabled = false;
                nextButton.classList.remove('opacity-50', 'cursor-not-allowed');
                nextButton.classList.add('hover:bg-green-600');
            }} else {{
                nextButton.disabled = true;
                nextButton.classList.add('opacity-50', 'cursor-not-allowed');
                nextButton.classList.remove('hover:bg-green-600');
            }}
        }}
        document.addEventListener('DOMContentLoaded', function() {{
            checkNextButton();
        }});
        async function submitAnnotation() {{
            let index = parseInt(document.getElementById('index').value);
            let payload = {{
                index: index,
                ContextualRelevance_rating: document.getElementById('ContextualRelevance_rating').value,
                PedagogicalQuality_rating: document.getElementById('PedagogicalQuality_rating').value,
                Actionability_rating: document.getElementById('Actionability_rating').value,
                CommunicationStyle_rating: document.getElementById('CommunicationStyle_rating').value,
                Comments: document.getElementById('Comments').value
            }};
            let resp = await fetch('/api/annotate', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify(payload)
            }});
            let data = await resp.json();
            if (data.status === 'success') {{
                navigate('next');
            }}
        }}
        async function navigate(direction) {{
            let resp = await fetch('/api/navigate', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{direction: direction}})
            }});
            let data = await resp.json();
            if (data.index !== undefined) {{
                window.location.href = '/annotate';
            }}
        }}
        async function skipAnnotation() {{
            let index = parseInt(document.getElementById('index').value);
            let payload = {{
                index: index,
                ContextualRelevance_rating: '',
                PedagogicalQuality_rating: '',
                Actionability_rating: '',
                CommunicationStyle_rating: '',
                Comments: ''
            }};
            let resp = await fetch('/api/annotate', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify(payload)
            }});
            let data = await resp.json();
            if (data.status === 'success') {{
                navigate('next');
            }}
        }}
        // Show confirmation modal for Finish and Save
        function showFinishConfirm() {{
            document.getElementById('finishConfirmModal').classList.remove('hidden');
        }}
        // If user confirms, proceed to finish
        async function confirmFinishYes() {{
            document.getElementById('finishConfirmModal').classList.add('hidden');
            let index = parseInt(document.getElementById('index').value);
            let payload = {{
                index: index,
                ContextualRelevance_rating: document.getElementById('ContextualRelevance_rating').value,
                PedagogicalQuality_rating: document.getElementById('PedagogicalQuality_rating').value,
                Actionability_rating: document.getElementById('Actionability_rating').value,
                CommunicationStyle_rating: document.getElementById('CommunicationStyle_rating').value,
                Comments: document.getElementById('Comments').value
            }};
            let resp = await fetch('/api/annotate', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify(payload)
            }});
            let data = await resp.json();
            if (data.status === 'success') {{
                window.location.href = '/finish';
            }}
        }}
        // If user cancels, hide modal and stay on annotation
        function confirmFinishNo() {{
            document.getElementById('finishConfirmModal').classList.add('hidden');
        }}
        </script>
    </body>
    </html>
    """

def render_rubric(get_rating):
    rubric = [
        ('ContextualRelevance', 'Contextual Relevance', [
            ('Excellent', 'Highly Localized'),
            ('Good', 'Generally Relevant'),
            ('Poor', 'Culturally Misaligned')
        ]),
        ('PedagogicalQuality', 'Pedagogical Quality', [
            ('Effective', 'Student-Centered & Modern'),
            ('Acceptable', 'Traditional but Safe'),
            ('Ineffective', 'Outdated or Poor Practice')
        ]),
        ('Actionability', 'Actionability', [
            ('VeryActionable', 'Clear & Practical'),
            ('SomewhatActionable', 'Theoretical'),
            ('NotActionable', 'Impractical or Vague')
        ]),
        ('CommunicationStyle', 'Communication Style', [
            ('Supportive', 'Supportive & Encouraging'),
            ('Neutral', 'Neutral & Factual'),
            ('Condescending', 'Condescending or Dismissive')
        ])
    ]
    # Arrange rubric in 2x2 grid
    btns = ["<div class='grid grid-cols-2 gap-6'>"]
    for i in range(2):
        btns.append("<div class='flex flex-col gap-2'>")
        for j in range(2):
            idx = i * 2 + j
            crit, label, options = rubric[idx]
            btns.append(
                f"<div>"
                f"<div class='mb-1 font-semibold'>{label}</div>"
                f"<div class='flex items-center gap-2 mb-2'>"
                f"<input type='hidden' id='{crit}_rating' name='{crit}_rating' value='{get_rating(crit)}'>"
            )
            for k, opt in enumerate(options):
                opt_label = opt[0]
                opt_text = opt[0]
                if opt_label == 'VeryActionable':
                    opt_text = 'Very Actionable'
                elif opt_label == 'SomewhatActionable':
                    opt_text = 'Somewhat Actionable'
                elif opt_label == 'NotActionable':
                    opt_text = 'Not Actionable'
                elif opt_label == 'Supportive':
                    opt_text = 'Supportive & Encouraging'
                elif opt_label == 'Neutral':
                    opt_text = 'Neutral & Factual'
                elif opt_label == 'Condescending':
                    opt_text = 'Condescending or Dismissive'
                # Determine ring and font color for selected button
                selected = get_rating(crit) == opt_label
                ring_class = ''
                font_class = ''
                if selected:
                    if k == 0:
                        ring_class = 'ring-2 ring-green-500'
                        font_class = 'text-green-800'
                    elif k == 1:
                        ring_class = 'ring-2 ring-gray-400'
                        font_class = 'text-gray-700'
                    elif k == 2:
                        ring_class = 'ring-2 ring-red-500'
                        font_class = 'text-red-600'
                btns.append(
                    f"<button type='button' id='{crit}_{opt_label}' onclick=\"handleRatingClick('{crit}','{opt_label}')\" "
                    f"class='px-3 py-1 rounded border {'bg-green-100 border-green-300' if selected and k == 0 else ''}{'bg-gray-100 border-gray-300' if not selected else ''}{' bg-gray-100 border-gray-300' if selected and k == 1 else ''}{' bg-red-50 border-red-300' if selected and k == 2 else ''} {font_class} {ring_class}'>"
                    f"{opt_text}</button>"
                )
            btns.append("</div></div>")
        btns.append("</div>")
    btns.append("</div>")
    return "".join(btns)

def render_previous_button(idx):
    if idx > 0:
        return '<button type="button" onclick="navigate(\'previous\')" class="bg-gray-300 text-gray-700 px-4 py-2 rounded hover:bg-gray-400">Previous</button>'
    return '<div></div>'

# Helper: Render finish page
def render_finish_page():
    return f"""
    <!DOCTYPE html>
    <html lang='en'>
    <head>
        <meta charset='UTF-8'>
        <meta name='viewport' content='width=device-width, initial-scale=1.0'>
        <title>Finish Annotation</title>
        <script src='https://cdn.tailwindcss.com'></script>
    </head>
    <body class='bg-gray-100 min-h-screen flex items-center justify-center'>
        <div class='bg-white shadow-lg rounded-lg p-8 w-full max-w-md'>
            <h1 class='text-2xl font-bold mb-6 text-center'>Finish Annotation</h1>
            <div class='flex flex-col gap-4'>
                <button onclick="window.location.href='/quit'" class='bg-red-500 text-white rounded p-3 hover:bg-red-600'>Quit without saving</button>
                <button onclick="window.location.href='/save'" class='bg-green-500 text-white rounded p-3 hover:bg-green-600'>Save</button>
            </div>
        </div>
    </body>
    </html>
    """

# Helper: Render save page
def render_save_page():
    # Check if already saved
    if session_state.get('file_saved', False):
        return render_save_success_page()
    
    return f"""
    <!DOCTYPE html>
    <html lang='en'>
    <head>
        <meta charset='UTF-8'>
        <meta name='viewport' content='width=device-width, initial-scale=1.0'>
        <title>Save Results</title>
        <script src='https://cdn.tailwindcss.com'></script>
    </head>
    <body class='bg-gray-100 min-h-screen flex items-center justify-center'>
        <div class='bg-white shadow-lg rounded-lg p-8 w-full max-w-md'>
            <h1 class='text-2xl font-bold mb-6 text-center'>Save Results</h1>
            <form action='/save-file' method='post' class='flex flex-col gap-4'>
                <label class='block text-gray-700'>Filename (without .csv extension)</label>
                <input type='text' name='filename' id='filename' required class='border rounded p-2' placeholder='Enter filename...'>
                <button type='submit' id='saveButton' class='bg-gray-400 text-white rounded p-3 cursor-not-allowed' disabled>Save</button>
            </form>
        </div>
        <script>
        document.getElementById('filename').addEventListener('input', function() {{
            const filename = this.value.trim();
            const saveButton = document.getElementById('saveButton');
            
            if (filename.length > 0) {{
                saveButton.disabled = false;
                saveButton.classList.remove('bg-gray-400', 'cursor-not-allowed');
                saveButton.classList.add('bg-blue-500', 'hover:bg-blue-600');
            }} else {{
                saveButton.disabled = true;
                saveButton.classList.remove('bg-blue-500', 'hover:bg-blue-600');
                saveButton.classList.add('bg-gray-400', 'cursor-not-allowed');
            }}
        }});
        </script>
    </body>
    </html>
    """

# Helper: Render goodbye page
def render_goodbye_page(action="saved"):
    message = "Your annotations have been saved successfully!" if action == "saved" else "You quit without saving. Your annotations have been lost."
    return f"""
    <!DOCTYPE html>
    <html lang='en'>
    <head>
        <meta charset='UTF-8'>
        <meta name='viewport' content='width=device-width, initial-scale=1.0'>
        <title>Goodbye</title>
        <script src='https://cdn.tailwindcss.com'></script>
    </head>
    <body class='bg-gray-100 min-h-screen flex items-center justify-center'>
        <div class='bg-white shadow-lg rounded-lg p-8 w-full max-w-md'>
            <h1 class='text-2xl font-bold mb-6 text-center'>Goodbye!</h1>
            <p class='text-gray-600 mb-6 text-center'>{message}</p>
            <div class='flex justify-center'>
                <button onclick="window.location.href='/restart'" class='bg-blue-500 text-white rounded p-3 hover:bg-blue-600'>Start New Annotation</button>
            </div>
        </div>
    </body>
    </html>
    """

# Helper: Render save success page
def render_save_success_page():
    filename = session_state.get('saved_filename', 'annotated_results')
    return f"""
    <!DOCTYPE html>
    <html lang='en'>
    <head>
        <meta charset='UTF-8'>
        <meta name='viewport' content='width=device-width, initial-scale=1.0'>
        <title>File Saved Successfully</title>
        <script src='https://cdn.tailwindcss.com'></script>
    </head>
    <body class='bg-gray-100 min-h-screen flex items-center justify-center'>
        <div class='bg-white shadow-lg rounded-lg p-8 w-full max-w-md'>
            <h1 class='text-2xl font-bold mb-6 text-center'>File Saved Successfully!</h1>
            <p class='text-gray-600 mb-6 text-center'>Your annotated results have been saved as "{filename}.csv"</p>
            <div class='flex justify-center'>
                <button onclick="window.location.href='/restart'" class='bg-blue-500 text-white rounded p-3 hover:bg-blue-600'>Start New Annotation</button>
            </div>
        </div>
    </body>
    </html>
    """

@app.get("/", response_class=HTMLResponse)
def index():
    if not session_state['data_rows']:
        return render_upload_page()
    else:
        return RedirectResponse('/annotate', status_code=302)

@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    content = await file.read()
    try:
        df = pd.read_csv(io.StringIO(content.decode('utf-8')))
    except Exception:
        return HTMLResponse(render_upload_page(error='Invalid CSV file. Please check the file format.'), status_code=400)
    
    # Check for required columns with exact name matching
    required_columns = ['UserQuestion', 'ModelAnswer']
    missing_columns = []
    available_columns = list(df.columns)
    
    for col in required_columns:
        if col not in df.columns:
            missing_columns.append(col)
    
    if missing_columns:
        error_msg = f'CSV file is missing required columns: {", ".join(missing_columns)}. Available columns: {", ".join(available_columns)}'
        return HTMLResponse(render_upload_page(error=error_msg), status_code=400)
    
    # Check if columns have data
    if df.empty:
        return HTMLResponse(render_upload_page(error='CSV file is empty. Please upload a file with data.'), status_code=400)
    
    session_state['data_rows'] = df.to_dict(orient='records')
    session_state['annotations'] = [{} for _ in range(len(session_state['data_rows']))]
    session_state['current_index'] = 0
    session_state['total_rows'] = len(session_state['data_rows'])
    session_state['columns'] = list(df.columns)
    session_state['filename'] = file.filename
    return RedirectResponse('/annotate', status_code=302)

@app.get("/annotate", response_class=HTMLResponse)
def annotate():
    if not session_state['data_rows']:
        return RedirectResponse('/', status_code=302)
    return render_annotation_page()

@app.post("/api/annotate")
async def api_annotate(request: Request):
    data = await request.json()
    idx = data.get('index', 0)
    ann = {
        'ContextualRelevance_rating': data.get('ContextualRelevance_rating',''),
        'PedagogicalQuality_rating': data.get('PedagogicalQuality_rating',''),
        'Actionability_rating': data.get('Actionability_rating',''),
        'CommunicationStyle_rating': data.get('CommunicationStyle_rating',''),
        'Comments': data.get('Comments',''),
    }
    if idx < len(session_state['annotations']):
        session_state['annotations'][idx] = ann
    else:
        session_state['annotations'].append(ann)
    return {"status": "success"}

@app.post("/api/navigate")
async def api_navigate(request: Request):
    data = await request.json()
    direction = data.get('direction')
    idx = session_state['current_index']
    total = session_state['total_rows']
    if direction == 'next':
        if idx < total - 1:
            session_state['current_index'] += 1
    elif direction == 'previous':
        if idx > 0:
            session_state['current_index'] -= 1
    idx = session_state['current_index']
    row = session_state['data_rows'][idx] if total > 0 else {'UserQuestion': '', 'ModelAnswer': ''}
    return {'index': idx, 'question': row.get('UserQuestion',''), 'answer': row.get('ModelAnswer','')}

@app.get("/finish", response_class=HTMLResponse)
def finish():
    if not session_state['data_rows']:
        return RedirectResponse('/', status_code=302)
    return render_finish_page()

@app.get("/save", response_class=HTMLResponse)
def save():
    if not session_state['data_rows']:
        return RedirectResponse('/', status_code=302)
    return render_save_page()

@app.post("/save-file")
async def save_file(filename: str = Form(...)):
    if not session_state['data_rows']:
        return RedirectResponse('/', status_code=302)
    
    # Check if already saved to prevent double saving
    if session_state.get('file_saved', False):
        return RedirectResponse('/save-success', status_code=302)
    
    df = pd.DataFrame(session_state['data_rows'])
    ann_df = pd.DataFrame(session_state['annotations'])
    out = pd.concat([df, ann_df], axis=1)
    buf = io.StringIO()
    out.to_csv(buf, index=False)
    buf.seek(0)
    # Store filename and mark as saved
    session_state['saved_filename'] = filename
    session_state['file_saved'] = True
    # Return the actual CSV file for download
    return StreamingResponse(iter([buf.getvalue()]), media_type='text/csv', headers={
        'Content-Disposition': f'attachment; filename="{filename}.csv"'
    })

@app.get("/save-file")
def save_file_get():
    if not session_state['data_rows']:
        return RedirectResponse('/', status_code=302)
    df = pd.DataFrame(session_state['data_rows'])
    ann_df = pd.DataFrame(session_state['annotations'])
    out = pd.concat([df, ann_df], axis=1)
    buf = io.StringIO()
    out.to_csv(buf, index=False)
    buf.seek(0)
    filename = session_state.get('saved_filename', 'annotated_results')
    return StreamingResponse(iter([buf.getvalue()]), media_type='text/csv', headers={
        'Content-Disposition': f'attachment; filename="{filename}.csv"'
    })

@app.get("/quit")
def quit():
    # Clear session state
    session_state.clear()
    session_state.update(get_default_state())
    return RedirectResponse('/goodbye?action=quit', status_code=302)

@app.get("/save-success", response_class=HTMLResponse)
def save_success():
    if not session_state.get('saved_filename'):
        return RedirectResponse('/', status_code=302)
    return render_save_success_page()

@app.get("/download-success")
def download_success():
    # This endpoint is called after the file download completes
    # It shows the success page
    return render_save_success_page()

@app.get("/restart")
def restart():
    # Clear session state completely
    session_state.clear()
    session_state.update(get_default_state())
    return RedirectResponse('/', status_code=302)

@app.get("/goodbye")
def goodbye(action: str = "saved"):
    return render_goodbye_page(action)

@app.get("/download")
def download():
    if not session_state['data_rows']:
        return RedirectResponse('/', status_code=302)
    df = pd.DataFrame(session_state['data_rows'])
    ann_df = pd.DataFrame(session_state['annotations'])
    out = pd.concat([df, ann_df], axis=1)
    buf = io.StringIO()
    out.to_csv(buf, index=False)
    buf.seek(0)
    filename = session_state.get('filename', 'results')
    return StreamingResponse(iter([buf.getvalue()]), media_type='text/csv', headers={
        'Content-Disposition': f'attachment; filename="annotated_{filename}.csv"'
    })

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 