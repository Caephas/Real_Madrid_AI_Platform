import pytest
from fastapi.testclient import TestClient
from backend.chatbot.api.chatbot_api import app

# Initialize the test client
client = TestClient(app)

def test_root_endpoint():
    """Test the root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Real Madrid Chatbot API is running!"}

def test_chat_endpoint_valid_request(mocker):
    """Test the /api/chatbot/chat endpoint with a valid request"""
    # Mock the Gradio Client's predict method
    mocker.patch(
        "backend.chatbot.api.chatbot_api.client.predict",
        return_value=[None, [{"content": "Mocked response"}]],
    )

    # Make a POST request
    payload = {"user_input": "Hello, chatbot!"}
    response = client.post("/api/chatbot/chat", json=payload)

    # Assertions
    assert response.status_code == 200
    assert response.json() == {
        "user_input": "Hello, chatbot!",
        "response": "Mocked response",
    }

def test_chat_endpoint_with_error(mocker):
    """Test the /api/chatbot/chat endpoint when an exception occurs"""
    # Mock the Gradio Client's predict method to raise an exception
    mocker.patch(
        "backend.chatbot.api.chatbot_api.client.predict",
        side_effect=Exception("Mocked exception"),
    )

    # Make a POST request
    payload = {"user_input": "Hello, chatbot!"}
    response = client.post("/api/chatbot/chat", json=payload)

    # Assertions
    assert response.status_code == 200
    assert response.json() == {"error": "Mocked exception"}