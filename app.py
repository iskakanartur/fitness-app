from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import cast, Date
from collections import defaultdict
import os
from datetime import datetime, date
from dotenv import load_dotenv

# Load environment variables from .env file for local development
load_dotenv()

# --- App & Database Configuration ---
app = Flask(__name__)

DATABASE_URL = os.environ.get('DATABASE_URL')

if not DATABASE_URL:
    raise RuntimeError("FATAL: DATABASE_URL environment variable is not set.")

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


# --- Simplified Database Model (No Sets) ---
class Workout(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    exercise_name = db.Column(db.String(100), nullable=False)
    reps = db.Column(db.Integer, nullable=False) # Total reps for this entry
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f'<Workout {self.exercise_name}>'


# Create database tables before any requests.
with app.app_context():
    db.create_all()


# --- Web Page Routes ---
@app.route('/')
def index():
    """Main page, displays workouts and daily summary."""
    all_workouts = Workout.query.order_by(Workout.timestamp.desc()).all()

    # --- Calculate Today's Stats for Chart and Table ---
    today = date.today()
    todays_workouts = Workout.query.filter(
        cast(Workout.timestamp, Date) == today
    ).all()

    # Simplified summary just tallies reps
    daily_summary = defaultdict(int)
    for workout in todays_workouts:
        daily_summary[workout.exercise_name] += workout.reps

    # Prepare data for Chart.js
    chart_labels = list(daily_summary.keys())
    chart_data = list(daily_summary.values())
    
    # Sort summary for consistent table display
    sorted_summary = sorted(daily_summary.items(), key=lambda item: item[0])

    return render_template(
        'index.html',
        workouts=all_workouts,
        sorted_summary=sorted_summary,
        chart_labels=chart_labels,
        chart_data=chart_data
    )


@app.route('/add', methods=['POST'])
def add_workout():
    """Handles adding a new workout entry."""
    exercise_name = request.form.get('exercise_name')
    reps = int(request.form.get('reps'))

    if exercise_name and reps:
        new_workout = Workout(exercise_name=exercise_name, reps=reps)
        db.session.add(new_workout)
        db.session.commit()
    return redirect(url_for('index'))


@app.route('/edit/<int:workout_id>')
def edit_workout(workout_id):
    """Displays the page to edit a workout."""
    workout = db.session.get(Workout, workout_id)
    if workout:
        return render_template('edit.html', workout=workout)
    return redirect(url_for('index'))


@app.route('/update/<int:workout_id>', methods=['POST'])
def update_workout(workout_id):
    """Handles updating a workout entry."""
    workout = db.session.get(Workout, workout_id)
    if workout:
        workout.exercise_name = request.form.get('exercise_name')
        workout.reps = int(request.form.get('reps'))
        db.session.commit()
    return redirect(url_for('index'))


@app.route('/delete/<int:workout_id>')
def delete_workout(workout_id):
    """Handles deleting a workout entry."""
    workout = db.session.get(Workout, workout_id)
    if workout:
        db.session.delete(workout)
        db.session.commit()
    return redirect(url_for('index'))

# --- Main Entry Point (for local development only) ---
if __name__ == '__main__':
    app.run(debug=True)

