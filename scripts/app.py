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