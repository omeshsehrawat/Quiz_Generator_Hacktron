import gradio as gr
from openai import OpenAI
import os
from dotenv import load_dotenv

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
            return "Error: Total questions must be positive."
        if easy_questions < 0 or medium_questions < 0 or hard_questions < 0:
            return "Error: Question counts cannot be negative."
        if easy_questions + medium_questions + hard_questions != total_questions:
            return "Error: The sum of Easy, Medium, and Hard questions must equal the total number of questions."

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

        # Format the response for display
        if not response.strip():
            return "Error: No response from the model."

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

        # Generate formatted output
        output = "# Generated Quiz\n\n"
        if easy:
            output += "## Easy Questions\n"
            for i, q in enumerate(easy, 1):
                output += f"**{i}. {q['text']}**  \nAnswer: *{q['answer']}*\n\n"
        if medium:
            output += "## Medium Questions\n"
            for i, q in enumerate(medium, 1):
                output += f"**{i}. {q['text']}**  \nAnswer: *{q['answer']}*\n\n"
        if hard:
            output += "## Hard Questions\n"
            for i, q in enumerate(hard, 1):
                output += f"**{i}. {q['text']}**  \nAnswer: *{q['answer']}*\n\n"

        return output

    except ValueError:
        return "Error: Please enter valid numbers for question counts."
    except Exception as e:
        return f"Error: An unexpected error occurred: {str(e)}"

# Define Gradio interface
with gr.Blocks(theme=gr.themes.Soft()) as demo:
    gr.Markdown("# AI-Powered Quiz Generator")
    gr.Markdown("Enter the quiz details below to generate a custom quiz.")

    with gr.Row():
        topic = gr.Textbox(label="Topic", placeholder="e.g., Photosynthesis")
        total_questions = gr.Number(label="Total Number of Questions", value=10, minimum=1, precision=0)

    with gr.Row():
        easy_questions = gr.Number(label="Easy Questions", value=4, minimum=0, precision=0)
        medium_questions = gr.Number(label="Medium Questions", value=3, minimum=0, precision=0)
        hard_questions = gr.Number(label="Hard Questions", value=3, minimum=0, precision=0)

    submit_btn = gr.Button("Generate Quiz")
    output = gr.Markdown(label="Quiz Output")

    submit_btn.click(
        fn=generate_quiz,
        inputs=[topic, total_questions, easy_questions, medium_questions, hard_questions],
        outputs=output
    )

# Launch the app
demo.launch()