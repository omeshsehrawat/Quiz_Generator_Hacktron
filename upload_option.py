import gradio as gr
from openai import OpenAI
import os
from dotenv import load_dotenv
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import tempfile
import PyPDF2
from docx.api import Document

# Load environment variables
load_dotenv()

# Initialize OpenAI client
MODEL = "llama3.2"
openai = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
system_message = "You are a helpful assistant"

def extract_text_from_file(file):
    """Extract text from uploaded file (PDF, TXT, or DOCX)."""
    if file is None:
        return ""
    
    file_path = file.name
    file_ext = os.path.splitext(file_path)[1].lower()
    
    try:
        if file_ext == '.pdf':
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() or ""
                return text
        elif file_ext == '.txt':
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        elif file_ext == '.docx':
            doc = Document(file_path)
            text = ""
            for para in doc.paragraphs:
                text += para.text + "\n"
            return text
        else:
            return "Error: Unsupported file format. Please upload a PDF, TXT, or DOCX file."
    except Exception as e:
        return f"Error: Failed to extract text from file: {str(e)}"

def generate_quiz(file, topic, total_questions, easy_questions, medium_questions, hard_questions):
    try:
        # Convert inputs to integers
        total_questions = int(total_questions)
        easy_questions = int(easy_questions)
        medium_questions = int(medium_questions)
        hard_questions = int(hard_questions)

        # Validate inputs
        if total_questions <= 0:
            return "Error: Total questions must be positive.", None
        if easy_questions < 0 or medium_questions < 0 or hard_questions < 0:
            return "Error: Question counts cannot be negative.", None
        if easy_questions + medium_questions + hard_questions != total_questions:
            return "Error: The sum of Easy, Medium, and Hard questions must equal the total number of questions.", None

        # Extract text from file if provided
        file_content = extract_text_from_file(file)
        if file_content.startswith("Error:"):
            return file_content, None

        # Use file content if provided, otherwise use topic
        if file_content:
            context = file_content[:2000]  # Limit context to avoid token limits
            prompt_topic = "the uploaded document"
        elif topic:
            context = ""
            prompt_topic = f"the topic '{topic}'"
        else:
            return "Error: Please provide either a topic or an uploaded file.", None

        # Generate prompt for the model
        message = (
            f"Generate {total_questions} questions based on {prompt_topic}. "
            f"Please make {easy_questions} easy questions, {medium_questions} medium questions, and {hard_questions} hard questions. "
            f"Format each question as follows:\n"
            f"- Difficulty: [Easy/Medium/Hard]\n"
            f"- Question: [Question text]\n"
            f"- Answer: [Answer text]\n"
        )
        if context:
            message += f"\nContext from the document:\n{context}\n"

        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": message}
        ]

        # Call the model
        stream = openai.chat.completions.create(
            model=MODEL,
            messages=messages,
            stream=True
        )

        # Collect response
        response = ""
        for chunk in stream:
            response += chunk.choices[0].delta.content or ''

        if not response.strip():
            return "Error: No response from the model.", None

        # Parse response into structured format
        questions = []
        lines = response.split('\n')
        current_question = {}
        for line in lines:
            line = line.strip()
            if line.startswith('- Difficulty:'):
                if current_question:
                    questions.append(current_question)
                current_question = {'difficulty': line.replace('- Difficulty:', '').strip().lower()}
            elif line.startswith('- Question:'):
                current_question['text'] = line.replace('- Question:', '').strip()
            elif line.startswith('- Answer:'):
                current_question['answer'] = line.replace('- Answer:', '').strip()
        if current_question:
            questions.append(current_question)

        # Group questions by difficulty
        easy = [q for q in questions if q['difficulty'] == 'easy']
        medium = [q for q in questions if q['difficulty'] == 'medium']
        hard = [q for q in questions if q['difficulty'] == 'hard']

        # Generate markdown output
        markdown_output = f"# Quiz on {prompt_topic}\n\n"
        if easy:
            markdown_output += "## Easy Questions\n"
            for i, q in enumerate(easy, 1):
                markdown_output += f"**{i}. {q['text']}**  \nAnswer: *{q['answer']}*\n\n"
        if medium:
            markdown_output += "## Medium Questions\n"
            for i, q in enumerate(medium, 1):
                markdown_output += f"**{i}. {q['text']}**  \nAnswer: *{q['answer']}*\n\n"
        if hard:
            markdown_output += "## Hard Questions\n"
            for i, q in enumerate(hard, 1):
                markdown_output += f"**{i}. {q['text']}**  \nAnswer: *{q['answer']}*\n\n"

        # Generate PDF
        pdf_file = create_pdf(prompt_topic, easy, medium, hard)
        return markdown_output, pdf_file

    except ValueError:
        return "Error: Please enter valid numbers for question counts.", None
    except Exception as e:
        return f"Error: An unexpected error occurred: {str(e)}", None

def create_pdf(topic, easy_questions, medium_questions, hard_questions):
    """Create a PDF file with the quiz content."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
        pdf_path = temp_file.name

    doc = SimpleDocTemplate(pdf_path, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph(f"Quiz on {topic}", styles['Title']))
    story.append(Spacer(1, 12))

    if easy_questions:
        story.append(Paragraph("Easy Questions", styles['Heading2']))
        for i, q in enumerate(easy_questions, 1):
            story.append(Paragraph(f"{i}. {q['text']}", styles['BodyText']))
            story.append(Paragraph(f"Answer: {q['answer']}", styles['Italic']))
            story.append(Spacer(1, 12))

    if medium_questions:
        story.append(Paragraph("Medium Questions", styles['Heading2']))
        for i, q in enumerate(medium_questions, 1):
            story.append(Paragraph(f"{i}. {q['text']}", styles['BodyText']))
            story.append(Paragraph(f"Answer: {q['answer']}", styles['Italic']))
            story.append(Spacer(1, 12))

    if hard_questions:
        story.append(Paragraph("Hard Questions", styles['Heading2']))
        for i, q in enumerate(hard_questions, 1):
            story.append(Paragraph(f"{i}. {q['text']}", styles['BodyText']))
            story.append(Paragraph(f"Answer: {q['answer']}", styles['Italic']))
            story.append(Spacer(1, 12))

    doc.build(story)
    return pdf_path

# Define Gradio interface
with gr.Blocks(theme=gr.themes.Soft()) as demo:
    gr.Markdown("# AI-Powered Quiz Generator")
    gr.Markdown("Enter a topic or upload a file (PDF, TXT, or DOCX) to generate a custom quiz and download it as a PDF.")

    with gr.Row():
        file_upload = gr.File(label="Upload File (Optional)", file_types=['.pdf', '.txt', '.docx'])
        topic = gr.Textbox(label="Topic (Optional)", placeholder="e.g., Photosynthesis")

    with gr.Row():
        total_questions = gr.Number(label="Total Number of Questions", value=10, minimum=1, precision=0)
        easy_questions = gr.Number(label="Easy Questions", value=4, minimum=0, precision=0)
        medium_questions = gr.Number(label="Medium Questions", value=3, minimum=0, precision=0)
        hard_questions = gr.Number(label="Hard Questions", value=3, minimum=0, precision=0)

    submit_btn = gr.Button("Generate Quiz")
    output = gr.Markdown(label="Quiz Output")
    pdf_output = gr.File(label="Download Quiz as PDF")

    submit_btn.click(
        fn=generate_quiz,
        inputs=[file_upload, topic, total_questions, easy_questions, medium_questions, hard_questions],
        outputs=[output, pdf_output]
    )

# Launch the app
demo.launch()