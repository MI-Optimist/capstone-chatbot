# pytest configuration — runs automatically before every test (autouse=True).
# Patches app.llm and app.vectordb with MagicMock objects so tests never make
# real Cohere API calls or hit the Chroma DB on disk.
# This keeps tests fast, offline, and deterministic.
import os
from dotenv import load_dotenv

load_dotenv()

import pytest
from unittest.mock import patch, MagicMock
from langchain_core.documents import Document


@pytest.fixture(autouse=True)
def mock_external_calls():
    mock_llm_response = MagicMock()
    mock_llm_response.content = "Test answer"

    mock_docs = [Document(page_content="Test document content")]

    with patch("app.llm.invoke", return_value=mock_llm_response), \
         patch("app.vectordb") as mock_vdb:
        mock_vdb.as_retriever.return_value.invoke.return_value = mock_docs
        mock_vdb.similarity_search.return_value = mock_docs
        yield