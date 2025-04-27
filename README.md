# Quiz_Generator_Hacktron

## 📚 AI Quiz Generator
This project is a powerful AI-driven quiz generator that can create customizable quizzes from uploaded files (PDF, DOCX, TXT) or a given topic.
It supports different types of questions (MCQ, True/False, Fill in the Blank, and Subjective) across various difficulty levels (Easy, Medium, Hard).

## Built using:

🧠 LLaMA3 model (via Ollama)

🎛️ Gradio for the web interface

🧾 ReportLab for PDF generation

📄 PyPDF2 and python-docx for document reading

## 🚀 Features
Upload a file (PDF, DOCX, TXT) or enter a custom topic.

Choose question type:
➔ Multiple Choice Questions (MCQ)
➔ True/False
➔ Fill in the Blank
➔ Subjective (short answer)

Select number of questions per difficulty (Easy, Medium, Hard).

Real-time AI question generation.

Download the quiz as a PDF.

Intelligent fallback: If the model fails, sensible placeholder questions are created.

Clean error handling and retry logic for model responses.

## 🛠️ Setup Instructions
- Clone the repository


    git clone https://github.com/your-username/ai-quiz-generator.git

    cd ai-quiz-generator

- Install the required packages


    pip install -r requirements.txt
- Set up environment variables

    Create a .env file:


- OPENAI_API_KEY=ollama  # Since using local Ollama
     OPENAI_BASE_URL=http://localhost:11434/v1
- Run the application


     python app.py
- Make sure Ollama is running with LLaMA3 model:


   ollama run llama3
## 🖥️ Tech Stack

Tech	Use
Python	Core programming language
Gradio	Building the web interface
ReportLab	Creating PDFs
PyPDF2	Reading PDFs
python-docx	Reading DOCX files
dotenv	Managing environment variables
OpenAI Python client	Communicating with local LLM (Ollama)
## 📸 Screenshots
![image](https://github.com/user-attachments/assets/d382a31a-4b37-4a85-bf08-ccbf8785f6fd)


## 📄 Example
Input:

Topic: "Photosynthesis"

Question Type: MCQ

10 Questions: 4 Easy, 3 Medium, 3 Hard

Output:

A ready-to-use quiz in Markdown and downloadable PDF.

##⚡ Future Improvements
Add support for LaTeX-based math questions.

Enhance PDF formatting (add page breaks, better headings).

Option to export quiz as DOCX or plain text.

Improve fallback questions using a local knowledge base.

Allow multi-topic quizzes.

## 🤝 Contributing
Contributions, issues, and feature requests are welcome!
Feel free to fork the repository and submit a pull request. 🚀

📜 License
This project is licensed under the MIT License.

✨ Acknowledgments
Thanks to Ollama for making LLaMA3 models easy to run locally.

Thanks to Gradio for making Python app building super easy.
