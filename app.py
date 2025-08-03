from flask import Flask, render_template, request, redirect, url_for, session, flash
import json
import os
import random

app = Flask(__name__)
app.secret_key = 'secretkey'

# 🔧 Set number of quiz questions (adjustable: 30, 40, or 60)
QUESTION_LIMIT = 60

# ✅ Use absolute paths for compatibility with local + Render
basedir = os.path.abspath(os.path.dirname(__file__))

# Load topics
with open(os.path.join(basedir, 'data', 'topics.json'), 'r', encoding='utf-8') as f:
    TOPICS = json.load(f)

# Load all questions
def load_questions():
    with open(os.path.join(basedir, 'data', 'questions.json'), 'r', encoding='utf-8') as f:
        return json.load(f)["questions"]

ALL_QUESTIONS = load_questions()

# Module-wise weightage
MODULE_WEIGHTAGE = {
    "Introduction to Stock Market": 8,
    "Types of Financial Markets": 7,
    "Equity Instruments": 5,
    "Corporate Actions": 5,
    "Equity Valuation Basics": 10,
    "Fundamental Analysis": 12,
    "Technical Analysis": 12,
    "Investment Strategies": 8,
    "Risk & Return": 8,
    "Trading and Investing in Equities": 7,
    "Tools & Trading Platforms": 5,
    "Regulatory Framework & Taxation": 5,
    "Psychology of Investing": 3,
    "Case Studies": 3,
    "Geopolitical Risk in Stock Market": 5,
    "Practical Market Strategies": 7
}

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        session['email'] = request.form['email']
        return redirect('/after_login')
    return render_template('login.html')

@app.route('/after_login')
def after_login():
    return render_template('after_login.html')

@app.route('/portfolio')
def portfolio():
    return render_template('under_progress.html')

@app.route('/select')
def select():
    return render_template('topic_selection.html', topics=TOPICS)

@app.route('/topics', methods=['GET', 'POST'])
def topics():
    if request.method == 'POST':
        selected = request.form.getlist('topics')
        if len(selected) < 3:
            flash('Please select at least 3 topics.')
            return redirect(url_for('topics'))

        filtered = [q for q in ALL_QUESTIONS if q['main_topic'] in selected]
        if not filtered:
            flash('No questions found for selected topics.')
            return redirect(url_for('topics'))

        total_weight = sum(MODULE_WEIGHTAGE[t] for t in selected)
        topic_question_map = {}
        float_alloc = {}

        for topic in selected:
            weight = MODULE_WEIGHTAGE[topic] / total_weight
            raw = weight * QUESTION_LIMIT
            float_alloc[topic] = raw
            topic_question_map[topic] = int(raw)

        # Distribute leftover questions
        total_allocated = sum(topic_question_map.values())
        remaining = QUESTION_LIMIT - total_allocated
        remainder_topics = sorted(float_alloc.items(), key=lambda x: x[1] - int(x[1]), reverse=True)
        for i in range(remaining):
            topic_question_map[remainder_topics[i][0]] += 1

        final_questions = []
        for topic, count in topic_question_map.items():
            topic_qs = [q for q in filtered if q["main_topic"] == topic]
            sampled = random.sample(topic_qs, min(count, len(topic_qs)))
            final_questions.extend(sampled)

        random.shuffle(final_questions)

        session['question_ids'] = [ALL_QUESTIONS.index(q) for q in final_questions]
        session['answers'] = []

        return redirect(url_for('show_question', index=0))

    topic_data = [{'main_topic': topic} for topic in MODULE_WEIGHTAGE.keys()]
    return render_template('topics.html', topics=topic_data)

@app.route('/question/<int:index>', methods=['GET', 'POST'])
def show_question(index):
    question_ids = session.get('question_ids')
    if not question_ids or index >= len(question_ids):
        flash('Session expired or invalid. Please select topics again.')
        return redirect(url_for('topics'))

    if request.method == 'POST':
        selected = request.form.get('selected', 'Not Answered')
        answers = session.get('answers', [])
        if len(answers) == index:
            answers.append(selected)
        elif len(answers) > index:
            answers[index] = selected
        session['answers'] = answers

        if index + 1 >= len(question_ids):
            return redirect(url_for('result'))
        return redirect(url_for('show_question', index=index + 1))

    question = ALL_QUESTIONS[question_ids[index]]
    return render_template('question.html', question=question, index=index, total=len(question_ids))

@app.route('/result')
def result():
    question_ids = session.get('question_ids')
    selected_answers = session.get('answers')

    if not question_ids or not selected_answers or len(selected_answers) != len(question_ids):
        flash("Session expired or incomplete attempt.")
        return redirect(url_for("topics"))

    results = []
    score = 0
    topic_stats = {}

    for idx, qid in enumerate(question_ids):
        q = ALL_QUESTIONS[qid]
        correct = q['answer']
        selected = selected_answers[idx] if idx < len(selected_answers) else "Not Answered"
        is_correct = selected == correct
        if is_correct:
            score += 1

        topic = q.get('main_topic', 'General')
        topic_stats.setdefault(topic, {'correct': 0, 'total': 0})
        topic_stats[topic]['total'] += 1
        if is_correct:
            topic_stats[topic]['correct'] += 1

        results.append({
            'question': q['question'],
            'options': q['options'],
            'correct': correct,
            'selected': selected,
            'is_correct': is_correct,
            'explanation': q.get('explanation', 'No explanation provided.'),
            'example': q.get('example', 'No example available.'),
            'main_topic': topic
        })

    feedback = []
    for topic, stat in topic_stats.items():
        acc = stat['correct'] / stat['total']
        if acc >= 0.8:
            feedback.append(f"✅ You performed well in <strong>{topic}</strong>.")
        elif acc >= 0.5:
            feedback.append(f"⚠️ You are average in <strong>{topic}</strong>.")
        else:
            feedback.append(f"❌ You are weak in <strong>{topic}</strong>. Focus on this area.")

    return render_template('result.html', results=results, feedback=feedback, score=score, total=len(question_ids))

# ✅ Final app runner
if __name__ == '__main__':
    app.run(debug=True)
