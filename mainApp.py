from flask import Flask
app = Flask("SmartBin")

@app.route("/") #app route si riferisce direttamente alla funzione
def home():
    return "<html><h1> Hello world </h1></html>"

@app.route("/prova")
def prova():
    return "<html><b> Pagina di prova <b></html>"