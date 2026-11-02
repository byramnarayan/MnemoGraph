import pytest
from app.services.llm.groq_client import GroqClient
from app.services.llm.prompt_builder import PromptBuilder


def test_groq_client_key_rotation():
    keys = ["key-alpha", "key-beta", "key-gamma"]
    client = GroqClient(api_keys=keys, model="openai/gpt-oss-120b")
    assert len(client.api_keys) == 3

    # Check round-robin index advancement
    idx1 = GroqClient.get_next_key_index()
    idx2 = GroqClient.get_next_key_index()
    assert (idx1 + 1) % 3 == idx2 % 3


def test_prompt_builder_structure():
    query = "Who owns the Databricks ingestion pipeline?"
    evidence = [
        {
            "document_id": "doc:notebook:123",
            "source_url": "https://databricks.workspace/123",
            "score": 0.88,
            "excerpt": "Databricks ingestion setup and configuration details.",
            "related_people": ["alice@company.com"],
            "related_teams": ["DataEng"],
            "related_projects": ["Lakehouse"],
        }
    ]
    graph_ctx = {
        "people": ["alice@company.com"],
        "teams": ["DataEng"],
        "projects": ["Lakehouse"],
        "relation_path": [{"from": "Person", "to": "Document", "relation": "OWNS"}],
    }

    messages = PromptBuilder.build_prompt(query, evidence, graph_ctx)
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert "graph_query" in messages[0]["content"]
    assert messages[1]["role"] == "user"
    assert "QUESTION" in messages[1]["content"]
    assert "alice@company.com" in messages[1]["content"]


def test_prompt_builder_empty_fallback():
    messages = PromptBuilder.build_prompt("Any question?", [], {})
    assert len(messages) == 2
    assert "No evidence" in messages[1]["content"]

