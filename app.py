from flask import Flask, render_template, request, redirect, url_for, send_file, jsonify
from flask_sqlalchemy import SQLAlchemy
import pyqrcode
import base64, png # Imports for freezing requirements.txt
from io import BytesIO
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///redirects.db'
db = SQLAlchemy(app)

class Redirect(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True)
    destination_url = db.Column(db.String(200))
    views = db.Column(db.Integer, default=0)  # Counter for views

    def __repr__(self):
        return f'<Redirect {self.name}>'

class RedirectionStats(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    redirect_id = db.Column(db.Integer, db.ForeignKey('redirect.id'))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    redirect = db.relationship('Redirect', backref=db.backref('stats', lazy=True))

    def __repr__(self):
        return f'<RedirectionStats redirect_id={self.redirect_id}, timestamp={self.timestamp}>'

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        redirect_id = request.form['redirect_id']
        destination_url = request.form['destination_url']

        # Update the destination URL of an existing redirect
        redirect_obj = db.session.query(Redirect).get(redirect_id)
        if redirect_obj:
            redirect_obj.destination_url = destination_url
            db.session.commit()

    # Retrieve all redirects from the database
    redirects = db.session.query(Redirect).all()
    return render_template('index.html', redirects=redirects)

@app.route('/r/<name>')
def redirect_url(name):
    # Find the redirect object based on the provided name
    redirect_obj = db.session.query(Redirect).filter_by(name=name).first()
    if redirect_obj:
        # Log redirection statistics
        stats = RedirectionStats(redirect=redirect_obj)
        db.session.add(stats)
        db.session.commit()
        redirect_obj.views += 1  # Increment the view counter
        db.session.commit()
        return redirect(redirect_obj.destination_url)
    else:
        return 'Invalid redirection URL.'

@app.route('/create', methods=['POST'])
def create_redirect():
    name = request.form['name']
    destination_url = request.form['destination_url']

    # Create a new redirect entry in the database
    redirect_obj = Redirect(name=name, destination_url=destination_url)
    db.session.add(redirect_obj)
    db.session.commit()

    return redirect(url_for('index'))

@app.route('/update', methods=['POST'])
def update_redirect():
    redirect_id = request.form['redirect_id']
    field = request.form['field']
    value = request.form['value']

    # Update a specific field of an existing redirect
    redirect_obj = db.session.query(Redirect).get(redirect_id)
    if redirect_obj:
        setattr(redirect_obj, field, value)
        db.session.commit()
        return jsonify({'message': 'Update successful'})

    return jsonify({'message': 'Update failed'})

@app.route('/delete/<name>', methods=['POST'])
def delete_redirect(name):
    # Delete a redirect from the database
    redirect_obj = db.session.query(Redirect).filter_by(name=name).first()
    if redirect_obj:
        db.session.delete(redirect_obj)
        db.session.commit()

    return redirect(url_for('index'))

@app.route('/generate_qr_code/<name>')
def generate_qr_code(name):
    # Generate a QR code for a redirect URL
    redirect_obj = db.session.query(Redirect).filter_by(name=name).first()
    if redirect_obj:
        default_redirect_url = url_for('redirect_url', name=name, _external=True)
        qr_code = pyqrcode.create(default_redirect_url)

        temp_file = BytesIO()
        qr_code.png(temp_file, scale=5)
        temp_file.seek(0)

        return send_file(temp_file, mimetype='image/png')

    return 'Invalid redirection URL.'

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Create the database tables if they don't exist
    app.run(host='0.0.0.0', port=5000)
