"""
One-time setup: creates the MongoDB Atlas Vector Search index used for Mimi's
semantic recall of previous questions (backs the `qa_memory` collection read
in MimiLLMSession._search_qa_by_topic()).

Usage:
    python setup_vector_index.py

If your Atlas cluster tier doesn't support driver-side index creation (common
on Shared/M0 tiers), this script prints the index definition instead — paste
it into: Atlas UI -> your cluster -> Search -> Create Search Index -> JSON
Editor (pick the `qa_memory` collection in your database).
"""
import os
import json
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

INDEX_NAME = "qa_memory_vector_index"
DB_NAME = "AlexiDB"
COLLECTION_NAME = "qa_memory"

# Must match: embedding model dims (text-embedding-3-small -> 1536) and the
# `student_id` filter used by $vectorSearch in mimi_llm_session.py.
INDEX_DEFINITION = {
    "fields": [
        {
            "type": "vector",
            "path": "embedding",
            "numDimensions": 1536,
            "similarity": "cosine",
        },
        {
            "type": "filter",
            "path": "student_id",
        },
    ]
}


def main():
    mongo_uri = os.environ.get("MONGODB_URI")
    if not mongo_uri or "localhost" in mongo_uri:
        print("Set MONGODB_URI to your Atlas connection string in .env first "
              "(Vector Search requires Atlas — it isn't available on a local mongod).")
        return

    client = MongoClient(mongo_uri)
    collection = client[DB_NAME][COLLECTION_NAME]

    try:
        from pymongo.operations import SearchIndexModel
        model = SearchIndexModel(
            definition=INDEX_DEFINITION,
            name=INDEX_NAME,
            type="vectorSearch",
        )
        collection.create_search_index(model)
        print(f"Requested creation of '{INDEX_NAME}' on {DB_NAME}.{COLLECTION_NAME}.")
        print("Index build can take a minute or two — check the Atlas UI's Search tab for status.")
    except Exception as e:
        print(f"Driver-side index creation failed: {e}")
        print("Your cluster tier likely doesn't support this via the driver — create it manually:")
        print("  Atlas UI -> your cluster -> Search -> Create Search Index -> JSON Editor")
        print(f"  Database: {DB_NAME}   Collection: {COLLECTION_NAME}   Index name: {INDEX_NAME}")
        print(json.dumps(INDEX_DEFINITION, indent=2))


if __name__ == "__main__":
    main()
