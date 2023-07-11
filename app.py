from flask import Flask, request, jsonify, render_template, make_response
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import csv
import io


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///predictions.db'
db = SQLAlchemy(app)

class Prediction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    prediction = db.Column(db.String(200), nullable=False)
    resolution_date = db.Column(db.DateTime, nullable=False)
    note = db.Column(db.String(500), nullable=True)
    status = db.Column(db.String(20), nullable=True)
    probability_updates = db.relationship('ProbabilityUpdate', backref='prediction', lazy=True)


class ProbabilityUpdate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    prediction_id = db.Column(db.Integer, db.ForeignKey('prediction.id'), nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    probability = db.Column(db.Float, nullable=False)


with app.app_context():
    db.create_all()

@app.route('/', methods=['GET'])
def home():
    return render_template('index.html')

@app.route('/add', methods=['GET'])
def add_prediction_form():
    return render_template('add_prediction.html')

@app.route('/prediction', methods=['POST'])
def add_prediction():
    data = request.form
    resolution_date = datetime.strptime(data['resolution_date'], '%Y/%m/%d')
    prediction = Prediction(prediction=data['prediction'], resolution_date=resolution_date, note=data['note'])
    db.session.add(prediction)
    db.session.commit()
    
    probability_update = ProbabilityUpdate(prediction_id=prediction.id, probability=float(data['probability']))
    db.session.add(probability_update)
    db.session.commit()
    
    return jsonify({'message': 'Prediction added'})


@app.route('/predictions', methods=['GET'])
def get_predictions():
    predictions = Prediction.query.all()
    probability_updates = {prediction.id: prediction.probability_updates for prediction in predictions}
    return render_template('predictions.html', predictions=predictions, probability_updates=probability_updates)


@app.route('/prediction/<int:id>', methods=['GET'])
def get_prediction(id):
    prediction = Prediction.query.get(id)
    most_recent_probability = prediction.probability_updates[-1].probability if prediction.probability_updates else None
    return render_template('prediction.html', prediction=prediction, probability_updates=prediction.probability_updates, most_recent_probability=most_recent_probability)



@app.route('/prediction/<int:id>', methods=['POST'])
def update_prediction(id):
    prediction = Prediction.query.get(id)
    data = request.form
    
    new_probability = float(data['probability'])
    if not prediction.probability_updates or new_probability != prediction.probability_updates[-1].probability:
        probability_update = ProbabilityUpdate(prediction_id=prediction.id, probability=new_probability)
        db.session.add(probability_update)
    
    prediction.prediction = data['prediction']
    prediction.resolution_date = datetime.strptime(data['resolution_date'], '%Y-%m-%d %H:%M:%S')
    prediction.note = data['note']
    prediction.status = data['status']
    db.session.commit()
    
    return jsonify({'message': 'Prediction updated'})

@app.route('/export', methods=['GET'])
def export_predictions():
    si = io.StringIO()
    cw = csv.writer(si)
    # write header
    cw.writerow(['id', 'prediction', 'resolution_date', 'note', 'status', 'probability_updates'])
    
    predictions = Prediction.query.all()
    for prediction in predictions:
        probability_updates_str = ';'.join(f'{pu.date}: {pu.probability}' for pu in prediction.probability_updates)
        cw.writerow([prediction.id, prediction.prediction, prediction.resolution_date, prediction.note, prediction.status, probability_updates_str])
        
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=predictions.csv"
    output.headers["Content-type"] = "text/csv"
    return output

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
