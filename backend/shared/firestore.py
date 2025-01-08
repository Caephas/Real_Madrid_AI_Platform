from firebase_admin import firestore, initialize_app

# Initialize Firebase using ADC (Application Default Credentials)
initialize_app()

# Firestore instance
db = firestore.client()

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
    collection = db.collection(collection_name)
    for doc in documents:
        doc_id = str(doc.get(id_field, "unknown_id"))
        collection.document(doc_id).set(doc)
    print(f"Stored {len(documents)} documents in the '{collection_name}' collection.")

def store_events_in_firestore(events):
    """
    Store live match events in Firestore.
    """
    match_events_collection = db.collection("MATCH_EVENTS")
    for event in events:
        event_id = f"{event['time']['elapsed']}_{event['type']}"
        match_events_collection.document(event_id).set(event)
    print(f"Stored {len(events)} events in Firestore.")