from fastapi import FastAPI
from mangum import Mangum
from api.recommendations_api import app as recommendations_app

app = FastAPI()
app.mount("/", recommendations_app)

handler = Mangum(app)