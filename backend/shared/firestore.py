import os
from firebase_admin import credentials, firestore, initialize_app
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

def initialize_firestore():
    """
    Initialize Firestore using credentials built dynamically from environment variables.
    """
    try:
        # Build the service account dictionary from environment variables
        service_account = {
            "type": os.getenv("FIREBASE_TYPE"),
            "project_id": os.getenv("FIREBASE_PROJECT_ID"),
            "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
            "private_key": os.getenv("FIREBASE_PRIVATE_KEY").replace("\\n", "\n"),
            "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
            "client_id": os.getenv("FIREBASE_CLIENT_ID"),
            "auth_uri": os.getenv("FIREBASE_AUTH_URI"),
            "token_uri": os.getenv("FIREBASE_TOKEN_URI"),
            "auth_provider_x509_cert_url": os.getenv("FIREBASE_AUTH_PROVIDER_X509_CERT_URL"),
            "client_x509_cert_url": os.getenv("FIREBASE_CLIENT_X509_CERT_URL"),
            "universe_domain": os.getenv("UNIVERSE_DOMAIN")
        }

        # Validate required fields
        missing_fields = [key for key, value in service_account.items() if not value]
        if missing_fields:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_fields)}")

        # Initialize Firebase using the dynamically constructed credentials
        cred = credentials.Certificate(service_account)
        initialize_app(cred)

        # Return the Firestore client
        return firestore.client()
    except Exception as e:
        raise RuntimeError(f"Failed to initialize Firestore: {e}")

# Initialize Firestore client
db = initialize_firestore()

def get_firestore():
    """Return the Firestore client."""
    return db

def store_documents(collection_name, documents, id_field="id"):
    """
    Store a list of documents in a Firestore collection.

    Args:
        collection_name (str): Name of the Firestore collection.
        documents (list): List of documents (dict) to store.
        id_field (str): Field in the document to use as Firestore document ID.
    """
    try:
        collection = db.collection(collection_name)
        for doc in documents:
            doc_id = str(doc.get(id_field, "unknown_id"))
            collection.document(doc_id).set(doc)
        print(f"Stored {len(documents)} documents in the '{collection_name}' collection.")
    except Exception as e:
        print(f"Error storing documents in Firestore: {e}")

def store_events_in_firestore(events):
    """
    Store live match events in Firestore.

    Args:
        events (list): List of event dictionaries to store.
    """
    try:
        match_events_collection = db.collection("MATCH_EVENTS")
        for event in events:
            event_id = f"{event['time']['elapsed']}_{event['type']}"
            match_events_collection.document(event_id).set(event)
        print(f"Stored {len(events)} events in Firestore.")
    except Exception as e:
        print(f"Error storing events in Firestore: {e}")