from flask import Flask
from flask import render_template

app = Flask("SmartBin")

@app.route("/") #app route si riferisce direttamente alla funzione
def home():
    return render_template('index.html')

@app.route("/index/")
def index():
    return home()

@app.route("/prova")
def prova():
    return "<html><b> Pagina di prova <b></html>"