import gradio as gr
from openai import OpenAI
import os
from dotenv import load_dotenv
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import tempfile
import PyPDF2
from docx import Document
from openai import OpenAIError
import time

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
                    extracted = page.extract_text()
                    if extracted:
                        text += extracted
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
            return "<span style='font-size: 20px; color: red;'>Error: Unsupported file format. Please upload a PDF, TXT, or DOCX file.</span>"
    except Exception as e:
        return f"<span style='font-size: 20px; color: red;'>Error: Failed to extract text from file: {str(e)}</span>"

def generate_fallback_question(difficulty, prompt_topic, question_type):
    """Generate a placeholder question for the specified type and difficulty."""
    if question_type == "Fill in the Blank":
        return {
            'difficulty': difficulty.lower(),
            'text': f"Fill in the blank: A key concept of {prompt_topic} is _____.",
            'answer': f"This is a placeholder {difficulty} fill-in-the-blank question."
        }
    elif question_type == "True/False":
        return {
            'difficulty': difficulty.lower(),
            'text': f"Is {prompt_topic} a key concept? (True/False)",
            'answer': "True"
        }
    elif question_type == "MCQ":
        return {
            'difficulty': difficulty.lower(),
            'text': f"What is a key aspect of {prompt_topic}?",
            'options': ["Option A", "Option B", "Option C", "Option D"],
            'answer': "Option A"
        }
    else:  # Subjective
        return {
            'difficulty': difficulty.lower(),
            'text': f"Explain a key concept related to {prompt_topic}.",
            'answer': f"This is a placeholder {difficulty} subjective question."
        }

def generate_quiz(file, topic, total_questions, easy_questions, medium_questions, hard_questions, question_type):
    try:
        # Convert inputs to integers
        total_questions = int(total_questions)
        easy_questions = int(easy_questions)
        medium_questions = int(medium_questions)
        hard_questions = int(hard_questions)

        # Validate inputs
        if total_questions <= 0:
            return "<span style='font-size: 20px; color: red;'>Error: Total questions must be positive.</span>", None
        if easy_questions < 0 or medium_questions < 0 or hard_questions < 0:
            return "<span style='font-size: 20px; color: red;'>Error: Question counts cannot be negative.</span>", None
        if easy_questions + medium_questions + hard_questions != total_questions:
            return "<span style='font-size: 20px; color: red;'>Error: The sum of Easy, Medium, and Hard questions must equal the total number of questions.</span>", None

        # Extract text from file if provided
        file_content = extract_text_from_file(file)
        if file_content.startswith("<span"):
            return file_content, None

        # Use file content if provided, otherwise use topic
        if file_content:
            context = file_content[:2000]  # Limit context
            prompt_topic = "the uploaded document"
        elif topic:
            context = ""
            prompt_topic = f"the topic '{topic}'"
        else:
            return "<span style='font-size: 20px; color: red;'>Error: Please provide either a topic or an uploaded file.</span>", None

        # Define question format based on type
        format_instructions = ""
        example = ""
        if question_type == "Fill in the Blank":
            format_instructions = (
                "Each question must be a fill-in-the-blank question with a single blank (_____) in the question text. "
                "The answer must be the word or short phrase that fills the blank."
            )
            example = (
                "- Difficulty: Easy\n"
                "- Question: The main source of energy for photosynthesis is _____.\n"
                "- Answer: Sunlight\n"
            )
        elif question_type == "True/False":
            format_instructions = (
                "Each question must be a true/false question. The answer must be 'True' or 'False'."
            )
            example = (
                "- Difficulty: Easy\n"
                "- Question: Photosynthesis occurs in the chloroplasts. (True/False)\n"
                "- Answer: True\n"
            )
        elif question_type == "MCQ":
            format_instructions = (
                "Each question must be a multiple-choice question with exactly 4 options labeled A, B, C, D. "
                "The question text must end with a question mark. "
                "The answer must be the correct option (e.g., 'A'). "
                "List options as: - Option A: [text], - Option B: [text], etc."
            )
            example = (
                "- Difficulty: Medium\n"
                "- Question: What gas is produced during photosynthesis?\n"
                "- Option A: Oxygen\n"
                "- Option B: Carbon Dioxide\n"
                "- Option C: Nitrogen\n"
                "- Option D: Hydrogen\n"
                "- Answer: A\n"
            )
        else:  # Subjective
            format_instructions = (
                "Each question must be a subjective question requiring a short descriptive answer (1-2 sentences). "
                "The answer must provide a concise response."
            )
            example = (
                "- Difficulty: Hard\n"
                "- Question: Explain the role of chlorophyll in photosynthesis.\n"
                "- Answer: Chlorophyll absorbs light energy, which is used to drive the photosynthesis process.\n"
            )

        # Generate prompt
        message = (
            f"Generate EXACTLY {total_questions} {question_type} questions based on {prompt_topic}. "
            f"You MUST create EXACTLY {easy_questions} Easy questions, {medium_questions} Medium questions, and {hard_questions} Hard questions. "
            f"{format_instructions} "
            "Each question MUST follow this EXACT format, with no extra text, introductions, or deviations:\n"
            f"{example}\n"
            "Ensure every question has a Difficulty, Question, and Answer line in this order, "
            f"{'and 4 options for MCQ questions' if question_type == 'MCQ' else ''}."
            "Do not include any additional text, headers, or formatting outside the specified structure."
        )
        if context:
            message += f"\nContext from the document (use this to generate relevant questions):\n{context}\n"

        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": message}
        ]

        # Retry logic
        max_retries = 3
        questions = []
        valid_difficulties = {'easy', 'medium', 'hard'}

        for attempt in range(1, max_retries + 1):
            try:
                print(f"Attempt {attempt} to generate questions...")
                stream = openai.chat.completions.create(
                    model=MODEL,
                    messages=messages,
                    stream=True,
                    temperature=0.3,
                    max_tokens=4000
                )

                # Collect response
                response = ""
                for chunk in stream:
                    content = chunk.choices[0].delta.content
                    if content:
                        response += content

                if not response.strip():
                    print("Attempt failed: No response from the model.")
                    continue

                print(f"Raw model response (Attempt {attempt}):\n{response}")

                # Parse response
                questions = []
                lines = response.split('\n')
                current_question = {}
                option_count = 0

                for i, line in enumerate(lines):
                    line = line.strip()
                    if not line:
                        continue
                    if line.startswith('- Difficulty:'):
                        if current_question.get('difficulty') and current_question.get('text') and current_question.get('answer'):
                            if question_type != "MCQ" or (question_type == "MCQ" and option_count == 4):
                                questions.append(current_question)
                        difficulty = line.replace('- Difficulty:', '').strip().lower()
                        if difficulty in valid_difficulties:
                            current_question = {'difficulty': difficulty}
                            option_count = 0
                            if question_type == "MCQ":
                                current_question['options'] = []
                        else:
                            current_question = {}
                    elif line.startswith('- Question:') and current_question:
                        current_question['text'] = line.replace('- Question:', '').strip()
                    elif line.startswith('- Option ') and current_question and question_type == "MCQ":
                        option_text = line.replace(f'- Option {chr(65 + option_count)}:', '').strip()
                        current_question['options'].append(option_text)
                        option_count += 1
                    elif line.startswith('- Answer:') and current_question:
                        current_question['answer'] = line.replace('- Answer:', '').strip()

                if current_question.get('difficulty') and current_question.get('text') and current_question.get('answer'):
                    if question_type != "MCQ" or (question_type == "MCQ" and option_count == 4):
                        questions.append(current_question)

                # Group questions by difficulty
                easy = [q for q in questions if q['difficulty'] == 'easy']
                medium = [q for q in questions if q['difficulty'] == 'medium']
                hard = [q for q in questions if q['difficulty'] == 'hard']

                if (len(easy) >= easy_questions and 
                    len(medium) >= medium_questions and 
                    len(hard) >= hard_questions):
                    print(f"Success: Got {len(easy)} easy, {len(medium)} medium, {len(hard)} hard questions.")
                    break
                else:
                    print(
                        f"Attempt {attempt} failed: Got {len(easy)} easy (needed {easy_questions}), "
                        f"{len(medium)} medium (needed {medium_questions}), {len(hard)} hard (needed {hard_questions})."
                    )
                    if attempt < max_retries:
                        time.sleep(2)
            except OpenAIError as e:
                print(f"Attempt {attempt} failed: Model request error: {str(e)}")
                if attempt < max_retries:
                    time.sleep(2)
                continue

        # Add fallback questions
        if len(easy) < easy_questions:
            for _ in range(easy_questions - len(easy)):
                easy.append(generate_fallback_question('easy', prompt_topic, question_type))
        if len(medium) < medium_questions:
            for _ in range(medium_questions - len(medium)):
                medium.append(generate_fallback_question('medium', prompt_topic, question_type))
        if len(hard) < hard_questions:
            for _ in range(hard_questions - len(hard)):
                hard.append(generate_fallback_question('hard', prompt_topic, question_type))

        # Validate final counts
        if (len(easy) < easy_questions or 
            len(medium) < medium_questions or 
            len(hard) < hard_questions):
            return (
                f"<span style='font-size: 20px; color: red;'>Error: Could not generate the requested number of questions after {max_retries} attempts. "
                f"Got {len(easy)} easy (needed {easy_questions}), {len(medium)} medium (needed {medium_questions}), "
                f"{len(hard)} hard (needed {hard_questions}).</span>", None
            )

        # Trim excess questions
        easy = easy[:easy_questions]
        medium = medium[:medium_questions]
        hard = hard[:hard_questions]

        # Generate markdown output with answer on a new line
        markdown_output = f"# {question_type} Quiz on {prompt_topic}\n\n"
        if easy:
            markdown_output += "## Easy Questions\n"
            for i, q in enumerate(easy, 1):
                markdown_output += f"**{i}. {q['text']}**\n\n"
                if question_type == "MCQ":
                    for j, opt in enumerate(q.get('options', [])):
                        markdown_output += f"- {chr(65 + j)}. {opt}\n"
                    markdown_output += "\n"
                markdown_output += f"Answer: *{q['answer']}*\n\n"
        if medium:
            markdown_output += "## Medium Questions\n"
            for i, q in enumerate(medium, 1):
                markdown_output += f"**{i}. {q['text']}**\n\n"
                if question_type == "MCQ":
                    for j, opt in enumerate(q.get('options', [])):
                        markdown_output += f"- {chr(65 + j)}. {opt}\n"
                    markdown_output += "\n"
                markdown_output += f"Answer: *{q['answer']}*\n\n"
        if hard:
            markdown_output += "## Hard Questions\n"
            for i, q in enumerate(hard, 1):
                markdown_output += f"**{i}. {q['text']}**\n\n"
                if question_type == "MCQ":
                    for j, opt in enumerate(q.get('options', [])):
                        markdown_output += f"- {chr(65 + j)}. {opt}\n"
                    markdown_output += "\n"
                markdown_output += f"Answer: *{q['answer']}*\n\n"

        # Generate PDF
        pdf_file = create_pdf(prompt_topic, easy, medium, hard, question_type)
        return markdown_output, pdf_file

    except ValueError:
        return "<span style='font-size: 20px; color: red;'>Error: Please enter valid numbers for question counts.</span>", None
    except Exception as e:
        return f"<span style='font-size: 20px; color: red;'>Error: An unexpected error occurred: {str(e)}</span>", None

def create_pdf(topic, easy_questions, medium_questions, hard_questions, question_type):
    """Create a PDF file with the quiz content."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
        pdf_path = temp_file.name

    doc = SimpleDocTemplate(pdf_path, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph(f"{question_type} Quiz on {topic}", styles['Title']))
    story.append(Spacer(1, 12))

    if easy_questions:
        story.append(Paragraph("Easy Questions", styles['Heading2']))
        story.append(Spacer(1, 12))
        for i, q in enumerate(easy_questions, 1):
            story.append(Paragraph(f"{i}. {q['text']}", styles['BodyText']))
            story.append(Spacer(1, 6))
            if question_type == "MCQ":
                for j, opt in enumerate(q.get('options', [])):
                    story.append(Paragraph(f"{chr(65 + j)}. {opt}", styles['BodyText']))
                story.append(Spacer(1, 6))
            story.append(Paragraph(f"Answer: {q['answer']}", styles['Italic']))
            story.append(Spacer(1, 12))

    if medium_questions:
        story.append(Paragraph("Medium Questions", styles['Heading2']))
        story.append(Spacer(1, 12))
        for i, q in enumerate(medium_questions, 1):
            story.append(Paragraph(f"{i}. {q['text']}", styles['BodyText']))
            story.append(Spacer(1, 6))
            if question_type == "MCQ":
                for j, opt in enumerate(q.get('options', [])):
                    story.append(Paragraph(f"{chr(65 + j)}. {opt}", styles['BodyText']))
                story.append(Spacer(1, 6))
            story.append(Paragraph(f"Answer: {q['answer']}", styles['Italic']))
            story.append(Spacer(1, 12))

    if hard_questions:
        story.append(Paragraph("Hard Questions", styles['Heading2']))
        story.append(Spacer(1, 12))
        for i, q in enumerate(hard_questions, 1):
            story.append(Paragraph(f"{i}. {q['text']}", styles['BodyText']))
            story.append(Spacer(1, 6))
            if question_type == "MCQ":
                for j, opt in enumerate(q.get('options', [])):
                    story.append(Paragraph(f"{chr(65 + j)}. {opt}", styles['BodyText']))
                story.append(Spacer(1, 6))
            story.append(Paragraph(f"Answer: {q['answer']}", styles['Italic']))
            story.append(Spacer(1, 12))

    doc.build(story)
    return pdf_path

# Define Gradio interface with a header bar and centered heading
with gr.Blocks(theme=gr.themes.Soft()) as demo:
    # Header bar with centered heading
    gr.Markdown(
        "<div style='background-color: #f0f0f0; padding: 15px; text-align: center; width: 100%;'>"
        "<span style='font-size: 24px; font-weight: bold; color: #000000'>AI-Powered Quiz Generator</span>"
        "</div>"
    )

    with gr.Row():
        # Left column: Input controls
        with gr.Column(scale=1, min_width=300):
            gr.Markdown(
                "<div style='text-align: center;'>"
                "<span style='font-size: 18px;'>Enter a topic or upload a file (PDF, TXT, or DOCX) to generate a custom quiz and download it as a PDF.</span>"
                "</div>"
            )
            file_upload = gr.File(label="Upload File (Optional)", file_types=['.pdf', '.txt', '.docx'])
            topic = gr.Textbox(label="Topic (Optional)", placeholder="e.g., Photosynthesis")
            total_questions = gr.Number(label="Total Number of Questions", value=1, minimum=1, precision=0)
            easy_questions = gr.Number(label="Easy Questions", value=0, minimum=0, precision=0)
            medium_questions = gr.Number(label="Medium Questions", value=0, minimum=0, precision=0)
            hard_questions = gr.Number(label="Hard Questions", value=0, minimum=0, precision=0)
            question_type = gr.Dropdown(
                choices=["Fill in the Blank", "True/False", "MCQ", "Subjective"],
                label="Question Type",
                value="MCQ"
            )
            submit_btn = gr.Button("Generate Quiz")

        # Right column: Output display
        with gr.Column(scale=2, min_width=600):
            output = gr.Markdown(label="Quiz Output")
            pdf_output = gr.File(label="Download Quiz as PDF")

    submit_btn.click(
        fn=generate_quiz,
        inputs=[file_upload, topic, total_questions, easy_questions, medium_questions, hard_questions, question_type],
        outputs=[output, pdf_output]
    )

# Launch the app
demo.launch()