import os
import json
import random
import traceback
from flask import Flask, render_template, request, redirect, url_for, session, flash
import openai
from dotenv import load_dotenv

# Lade Umgebungsvariablen
load_dotenv()

# OpenAI API-Key aus Umgebungsvariablen lesen
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY nicht gesetzt!")



app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "fallback-secret")  # Sicherer Schlüssel

def generate_question(difficulty, topic):
    prompt = "Generiere eine abwechslungsreiche Multiple-Choice Frage für die PCEP Prüfung. "
    if difficulty != "alle":
        prompt += f" Die Frage soll den Schwierigkeitsgrad '{difficulty}' haben."
    if topic != "alle":
        prompt += f" Die Frage soll zum Themenbereich '{topic}' gehören."
    
    prompt += (
        " Es sollen vier Antwortmöglichkeiten generiert werden, von denen nur eine korrekt ist. "
        "Gib die Ausgabe als JSON zurück, im Format: "
        '{"question": "<Fragetext>", "choices": ["Antwort1", "Antwort2", "Antwort3", "Antwort4"], "correct": "<korrekte Antwort>"} '
        "ohne zusätzliche Erläuterungen oder Kommentare."
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Du bist ein Experte für PCEP Prüfungsfragen."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,  # Optimierte Tokenanzahl
        )
        content = response.choices[0].message.content
        question_data = json.loads(content)
        return question_data
    except Exception as e:
        print("Fehler beim Generieren oder Parsen der Frage:", e)
        traceback.print_exc()
        return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start', methods=['POST'])
def start():
    difficulty = request.form.get('difficulty')
    topic = request.form.get('topic')
    godmode = request.form.get('godmode')

    if godmode == "on":
        difficulty = "alle"
        topic = "alle"

    questions = []
    for _ in range(20):
        for attempt in range(3):
            q = generate_question(difficulty, topic)
            if q and "question" in q and "choices" in q and "correct" in q:
                duplicate = any(existing["question"].strip() == q["question"].strip() for existing in questions)
                if not duplicate:
                    questions.append(q)
                    break

    session['questions'] = questions
    session['answers'] = {}
    session['current_question'] = 0
    session['quiz_paused'] = False
    session['chat'] = []
    session['score'] = 0

    return redirect(url_for('quiz'))

@app.route('/quiz')
def quiz():
    if session.get('quiz_paused', False):
        return render_template('chat.html', chat=session.get('chat', []))
    
    current_index = session.get('current_question', 0)
    questions = session.get('questions', [])
    
    if current_index >= len(questions):
        return redirect(url_for('results'))
    
    return render_template('quiz.html', 
                           question=questions[current_index], 
                           index=current_index + 1,
                           total=len(questions),
                           score=session.get('score', 0))

@app.route('/submit_answer', methods=['POST'])
def submit_answer():
    chosen_answer = request.form.get('answer')
    current_index = session.get('current_question', 0)
    questions = session.get('questions', [])
    
    if current_index >= len(questions):
        return redirect(url_for('results'))
    
    correct_answer = questions[current_index]['correct']
    session['answers'][str(current_index)] = {
        'question': questions[current_index]['question'],
        'choices': questions[current_index]['choices'],
        'selected': chosen_answer,
        'correct': correct_answer,
        'is_correct': chosen_answer == correct_answer
    }
    
    if chosen_answer == correct_answer:
        session['score'] = session.get('score', 0) + 1
    
    session['current_question'] = current_index + 1
    return redirect(url_for('quiz'))

@app.route('/results')
def results():
    return render_template('results.html', answers=session.get('answers', {}), score=session.get('score', 0), total=len(session.get('questions', [])))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.getenv("PORT", 5000)))
