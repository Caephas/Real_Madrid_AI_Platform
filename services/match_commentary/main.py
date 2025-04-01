from fastapi import FastAPI
from mangum import Mangum
from api.match_commentary_api import app as commentary_app

app = FastAPI()
app.mount("/", commentary_app)

handler = Mangum(app)