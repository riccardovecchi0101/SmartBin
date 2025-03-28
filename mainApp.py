import secrets

from flask import Flask, render_template, request, redirect, url_for, flash
from flask_migrate import Migrate

from models import *

secret_key = secrets.token_hex(16)  # good for develop, bad for production (ma stica)

allowed_uids = ['9f1f8ec7-7ad1-48d0-bb4a-4f57c8e77d8c', '8cbbac49-b06f-4cb4-b93d-1c641b205ef9']
app = Flask("SmartBin")
app.config['SECRET_KEY'] = secret_key
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite3'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
migrate = Migrate(app, db)


@app.route("/")  # app route si riferisce direttamente alla funzione
def home():
    return render_template('index.html')


@app.route("/index")
def index():
    return home()


@app.errorhandler(404)
def handle_404(e):
    return home()

@app.route("/firstAccess", methods=['GET', 'POST'])
def firstAccess():
    if request.method == 'POST':
        uuid_input = request.form.get('uuid')
        inserviente = Inserviente.query.filter_by(uuid=uuid_input).first()

        if uuid_input not in allowed_uids:
            print("ehi")
            flash("UUID non valido!", "danger")
            return redirect(url_for('firstAccess'))

        if inserviente and inserviente.username:
            flash("UUID già registrato. Effettua il login.", "warning")
            return redirect(url_for('login'))

        return redirect(url_for('signup', uuid=uuid_input))

    return render_template('firstAccess.html')

@app.route("/signup/<uuid>", methods=['GET', 'POST'])
def signup(uuid):
    if request.method == 'POST':
        UUID = uuid
        name = request.form.get('name')
        surname = request.form.get('surname')
        username = request.form.get('username')
        password = request.form.get('password')

        print(UUID+'\t'+name+'\t'+surname+'\t'+username+'\t'+password)
        
        

      
    return render_template('signup.html')

@app.route("/login", methods=['GET', 'POST'])
def login():
    return render_template('login.html')

@app.get('/hq/<id>')
def hq(id):
    pass



with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
