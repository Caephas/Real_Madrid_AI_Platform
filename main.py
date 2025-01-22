from fastapi import FastAPI
from backend.chatbot.api.chatbot_api import app as chatbot_app
from backend.match_commentary.api.match_commentary_api import app as match_commentary_app
from backend.performance_prediction.api.match_prediction_api import app as match_prediction_app
from backend.personalized_content.api.recommendations_api import app as recommendations_app

app = FastAPI()

# Include each API as a router
app.mount("/chatbot", chatbot_app)
app.mount("/commentary", match_commentary_app)
app.mount("/prediction", match_prediction_app)
app.mount("/recommendations", recommendations_app)