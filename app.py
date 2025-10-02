from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from collections import defaultdict
import os
from datetime import datetime

# --- App & Database Configuration ---
app = Flask(__name__)

# This is the key change for deployment.
# 1. It looks for a 'DATABASE_URL' environment variable (which Render will provide).
# 2. If it can't find it, it falls back to your local database for development.
DATABASE_URL = os.environ.get(
    'DATABASE_URL', 
    'postgresql://postgres:HayastaN77@localhost/fitness_tracker' # Your local password is safe here.
)

# SQLAlchemy requires 'postgresql' but some services use 'postgres'. This line fixes that.
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize the database
db = SQLAlchemy(app)

# --- Database Model ---
class Workout(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    exercise_name = db.Column(db.String(100), nullable=False)
    sets = db.Column(db.Integer, nullable=False, default=1)
    reps = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f'<Workout {self.exercise_name}>'

# --- Web Page Routes ---
@app.route('/')
def index():
    """Main page, displays all workouts."""
    workouts = Workout.query.order_by(Workout.timestamp.desc()).all()
    return render_template('index.html', workouts=workouts)

@app.route('/add', methods=['POST'])
def add_workout():
    """Handles adding a new workout entry."""
    exercise_name = request.form.get('exercise_name')
    sets_str = request.form.get('sets')
    sets = int(sets_str) if sets_str and sets_str.isdigit() else 1
    reps = int(request.form.get('reps'))

    new_workout = Workout(exercise_name=exercise_name, sets=sets, reps=reps)
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
        sets_str = request.form.get('sets')
        workout.sets = int(sets_str) if sets_str and sets_str.isdigit() else 1
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


# --- API Endpoint for Stats ---
@app.route('/stats/grouped_by_date')
def stats_grouped_by_date():
    """
    Provides statistics grouped by date for a multi-bar chart.
    """
    workouts = Workout.query.order_by(Workout.timestamp).all()
    
    stats_agg = defaultdict(lambda: defaultdict(int))
    all_dates = set()
    
    for workout in workouts:
        date_str = workout.timestamp.strftime('%b %d')
        all_dates.add(date_str)
        total_reps = workout.sets * workout.reps
        stats_agg[workout.exercise_name][date_str] += total_reps
        
    sorted_labels = sorted(list(all_dates))
    
    datasets = []
    colors = [
        {'bg': 'rgba(255, 99, 132, 0.6)', 'border': 'rgba(255, 99, 132, 1)'},
        {'bg': 'rgba(54, 162, 235, 0.6)', 'border': 'rgba(54, 162, 235, 1)'},
        {'bg': 'rgba(255, 206, 86, 0.6)', 'border': 'rgba(255, 206, 86, 1)'},
        {'bg': 'rgba(75, 192, 192, 0.6)', 'border': 'rgba(75, 192, 192, 1)'},
        {'bg': 'rgba(153, 102, 255, 0.6)', 'border': 'rgba(153, 102, 255, 1)'},
        {'bg': 'rgba(255, 159, 64, 0.6)', 'border': 'rgba(255, 159, 64, 1)'}
    ]
    color_index = 0

    for exercise_name, date_data in stats_agg.items():
        data_points = [date_data.get(date_label, 0) for date_label in sorted_labels]
        
        color = colors[color_index % len(colors)]
        
        datasets.append({
            'label': exercise_name,
            'data': data_points,
            'backgroundColor': color['bg'],
            'borderColor': color['border'],
            'borderWidth': 1
        })
        color_index += 1

    chart_data = {
        'labels': sorted_labels,
        'datasets': datasets
    }
        
    return jsonify(chart_data)


# --- Main Entry Point ---
# The db.create_all() call is safe to keep; it will only create tables if they don't already exist.
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    # Debug mode should be OFF for production, but Render will handle this.
    app.run(debug=True)

