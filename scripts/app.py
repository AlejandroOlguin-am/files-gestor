import os
from typing import Union
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

@app.get("/familia")
def get_familia():
    rows = ["Alejandro", "Felicia", "Emiliana"]
    return rows

@app.get("/genios")
def get_genios():
    rows = ["Newton", "Einstein", "Tesla", "Curie", "Edison", "Leonardo da Vinci", "Galileo", "Hawking", "Turing"]
    return rows

@app.get("/frutas")
def get_frutas():
    rows = ["Manzana", "Banana", "Cereza", "Dátil", "Elderberry"]
    return rows

@app.get("/multimillonarios")
def get_multimillonarios():
    rows = ["Bill Gates", "Elon Musk", "Jeff Bezos", "Warret Buffet", "Carlos Slim"]
    return rows