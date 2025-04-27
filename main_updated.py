import gradio as gr
from openai import OpenAI
import os
from dotenv import load_dotenv
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import tempfile

# Load environment variables
load_dotenv()

# Initialize OpenAI client
MODEL = "llama3.2"
openai = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
system_message = "You are a helpful assistant"

def generate_quiz(topic, total_questions, easy_questions, medium_questions, hard_questions):
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

        # Generate prompt for the model
        message = (
            f"Generate {total_questions} questions on the topic '{topic}'. "
            f"Please make {easy_questions} easy questions, {medium_questions} medium questions, and {hard_questions} hard questions. "
            f"Format each question as follows:\n"
            f"- Difficulty: [Easy/Medium/Hard]\n"
            f"- Question: [Question text]\n"
            f"- Answer: [Answer text]\n"
        )
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
        markdown_output = f"# Quiz on {topic}\n\n"
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
        pdf_file = create_pdf(topic, easy, medium, hard)
        return markdown_output, pdf_file

    except ValueError:
        return "Error: Please enter valid numbers for question counts.", None
    except Exception as e:
        return f"Error: An unexpected error occurred: {str(e)}", None

def create_pdf(topic, easy_questions, medium_questions, hard_questions):
    # Create a temporary file for the PDF
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
        pdf_path = temp_file.name

    # Initialize PDF document
    doc = SimpleDocTemplate(pdf_path, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    # Add title
    story.append(Paragraph(f"Quiz on {topic}", styles['Title']))
    story.append(Spacer(1, 12))

    # Add easy questions
    if easy_questions:
        story.append(Paragraph("Easy Questions", styles['Heading2']))
        for i, q in enumerate(easy_questions, 1):
            story.append(Paragraph(f"{i}. {q['text']}", styles['BodyText']))
            story.append(Paragraph(f"Answer: {q['answer']}", styles['Italic']))
            story.append(Spacer(1, 12))

    # Add medium questions
    if medium_questions:
        story.append(Paragraph("Medium Questions", styles['Heading2']))
        for i, q in enumerate(medium_questions, 1):
            story.append(Paragraph(f"{i}. {q['text']}", styles['BodyText']))
            story.append(Paragraph(f"Answer: {q['answer']}", styles['Italic']))
            story.append(Spacer(1, 12))

    # Add hard questions
    if hard_questions:
        story.append(Paragraph("Hard Questions", styles['Heading2']))
        for i, q in enumerate(hard_questions, 1):
            story.append(Paragraph(f"{i}. {q['text']}", styles['BodyText']))
            story.append(Paragraph(f"Answer: {q['answer']}", styles['Italic']))
            story.append(Spacer(1, 12))

    # Build PDF
    doc.build(story)
    return pdf_path

# Define Gradio interface
with gr.Blocks(theme=gr.themes.Soft()) as demo:
    gr.Markdown("# AI-Powered Quiz Generator")
    gr.Markdown("Enter the quiz details below to generate a custom quiz and download it as a PDF.")

    with gr.Row():
        topic = gr.Textbox(label="Topic", placeholder="e.g., Photosynthesis")
        total_questions = gr.Number(label="Total Number of Questions", value=10, minimum=1, precision=0)

    with gr.Row():
        easy_questions = gr.Number(label="Easy Questions", value=4, minimum=0, precision=0)
        medium_questions = gr.Number(label="Medium Questions", value=3, minimum=0, precision=0)
        hard_questions = gr.Number(label="Hard Questions", value=3, minimum=0, precision=0)

    submit_btn = gr.Button("Generate Quiz")
    output = gr.Markdown(label="Quiz Output")
    pdf_output = gr.File(label="Download Quiz as PDF")

    submit_btn.click(
        fn=generate_quiz,
        inputs=[topic, total_questions, easy_questions, medium_questions, hard_questions],
        outputs=[output, pdf_output]
    )

# Launch the app
demo.launch()