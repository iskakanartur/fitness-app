from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import cast, Date
from collections import defaultdict
import os
from datetime import datetime, date
from dotenv import load_dotenv
import pytz # Import the new library

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

# --- Timezone Configuration ---
# Define the target timezone for Armenia
YEREVAN_TZ = pytz.timezone('Asia/Yerevan')


# --- Database Models ---
class Workout(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    exercise_name = db.Column(db.String(100), nullable=False)
    reps = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f'<Workout {self.exercise_name}>'

class Meal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    component1 = db.Column(db.String(100))
    component2 = db.Column(db.String(100))
    component3 = db.Column(db.String(100))
    component4 = db.Column(db.String(100))
    component5 = db.Column(db.String(100))
    calories = db.Column(db.Integer)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f'<Meal {self.name}>'


# Create database tables before any requests.
with app.app_context():
    db.create_all()

# --- Helper Function ---
def format_timedelta(td):
    """Formats a timedelta object into a readable string like '14h 32m'."""
    if td is None:
        return "N/A"
    total_seconds = int(td.total_seconds())
    days, remainder = divmod(total_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, _ = divmod(remainder, 60)
    if days > 0:
        return f"{days}d {hours}h {minutes}m"
    return f"{hours}h {minutes}m"


# --- Main Route ---
@app.route('/')
def index():
    # --- Workout Data ---
    all_workouts = Workout.query.order_by(Workout.timestamp.desc()).all()
    # Convert timestamps to local Armenian time for display
    for workout in all_workouts:
        workout.timestamp = workout.timestamp.replace(tzinfo=pytz.utc).astimezone(YEREVAN_TZ)

    today = date.today()
    todays_workouts = [w for w in all_workouts if w.timestamp.date() == today]
    
    workout_summary = defaultdict(int)
    for workout in todays_workouts:
        workout_summary[workout.exercise_name] += workout.reps
    sorted_workout_summary = sorted(workout_summary.items(), key=lambda item: item[0])
    chart_labels = list(workout_summary.keys())
    chart_data = list(workout_summary.values())

    # --- Meal Data ---
    meals_asc = Meal.query.order_by(Meal.timestamp.asc()).all()
    # Convert meal timestamps to local Armenian time *before* calculating differences
    for meal in meals_asc:
        meal.timestamp = meal.timestamp.replace(tzinfo=pytz.utc).astimezone(YEREVAN_TZ)

    meals_with_fasting_time = []
    for i, meal in enumerate(meals_asc):
        fasted_time = None
        if i > 0:
            time_diff = meal.timestamp - meals_asc[i-1].timestamp
            fasted_time = format_timedelta(time_diff)
        
        meals_with_fasting_time.append({
            'meal': meal,
            'fasted_time': fasted_time
        })
    
    meals_with_fasting_time.reverse()

    return render_template(
        'index.html',
        workouts=all_workouts,
        sorted_summary=sorted_workout_summary,
        chart_labels=chart_labels,
        chart_data=chart_data,
        meals_with_fasting_time=meals_with_fasting_time
    )


# --- Workout Routes ---
@app.route('/add_workout', methods=['POST'])
def add_workout():
    exercise_name = request.form.get('exercise_name')
    reps_str = request.form.get('reps')
    if exercise_name and reps_str and reps_str.isdigit():
        new_workout = Workout(exercise_name=exercise_name, reps=int(reps_str))
        db.session.add(new_workout)
        db.session.commit()
    return redirect(url_for('index'))

@app.route('/edit_workout/<int:workout_id>')
def edit_workout(workout_id):
    workout = db.session.get(Workout, workout_id)
    if workout:
        return render_template('edit_workout.html', workout=workout)
    return redirect(url_for('index'))

@app.route('/update_workout/<int:workout_id>', methods=['POST'])
def update_workout(workout_id):
    workout = db.session.get(Workout, workout_id)
    if workout:
        workout.exercise_name = request.form.get('exercise_name')
        reps_str = request.form.get('reps')
        if reps_str and reps_str.isdigit():
            workout.reps = int(reps_str)
        db.session.commit()
    return redirect(url_for('index'))

@app.route('/delete_workout/<int:workout_id>')
def delete_workout(workout_id):
    workout = db.session.get(Workout, workout_id)
    if workout:
        db.session.delete(workout)
        db.session.commit()
    return redirect(url_for('index'))


# --- Meal Routes ---
@app.route('/add_meal', methods=['POST'])
def add_meal():
    name = request.form.get('meal_name')
    calories = request.form.get('calories')
    if name:
        new_meal = Meal(
            name=name,
            component1=request.form.get('component1'),
            component2=request.form.get('component2'),
            component3=request.form.get('component3'),
            component4=request.form.get('component4'),
            component5=request.form.get('component5'),
            calories=int(calories) if calories and calories.isdigit() else None
        )
        db.session.add(new_meal)
        db.session.commit()
    return redirect(url_for('index'))

@app.route('/edit_meal/<int:meal_id>')
def edit_meal(meal_id):
    meal = db.session.get(Meal, meal_id)
    if meal:
        return render_template('edit_meal.html', meal=meal)
    return redirect(url_for('index'))

@app.route('/update_meal/<int:meal_id>', methods=['POST'])
def update_meal(meal_id):
    meal = db.session.get(Meal, meal_id)
    if meal:
        meal.name = request.form.get('meal_name')
        meal.component1=request.form.get('component1')
        meal.component2=request.form.get('component2')
        meal.component3=request.form.get('component3')
        meal.component4=request.form.get('component4')
        meal.component5=request.form.get('component5')
        calories = request.form.get('calories')
        meal.calories=int(calories) if calories and calories.isdigit() else None
        db.session.commit()
    return redirect(url_for('index'))

@app.route('/delete_meal/<int:meal_id>')
def delete_meal(meal_id):
    meal = db.session.get(Meal, meal_id)
    if meal:
        db.session.delete(meal)
        db.session.commit()
    return redirect(url_for('index'))

# --- Main Entry Point (for local development only) ---
if __name__ == '__main__':
    app.run(debug=True)

