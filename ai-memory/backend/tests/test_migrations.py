"""Verify Alembic migration revision chain."""

from alembic.config import Config
from alembic.script import ScriptDirectory


def test_migration_revision_chain():
    config = Config("alembic.ini")
    script = ScriptDirectory.from_config(config)

    heads = script.get_heads()
    assert heads == ["007_create_prompt_versions"]

    accounts_revision = script.get_revision("001_create_accounts")
    assert accounts_revision.down_revision is None
    assert accounts_revision.doc == "create accounts table"

    content_revision = script.get_revision("002_create_content_tables")
    assert content_revision.down_revision == "001_create_accounts"
    assert content_revision.doc == "create content memory and performance tables"

    sync_logs_revision = script.get_revision("003_create_sync_logs")
    assert sync_logs_revision.down_revision == "002_create_content_tables"
    assert sync_logs_revision.doc == "create sync logs table"

    learning_revision = script.get_revision("004_create_learning_tables")
    assert learning_revision.down_revision == "003_create_sync_logs"
    assert learning_revision.doc == "create brain learning and account profile tables"

    prediction_knowledge_revision = script.get_revision(
        "005_create_prediction_knowledge"
    )
    assert prediction_knowledge_revision.down_revision == "004_create_learning_tables"
    assert (
        prediction_knowledge_revision.doc
        == "create prediction and knowledge evolution tables"
    )

    trend_topics_revision = script.get_revision("006_create_trend_topics")
    assert trend_topics_revision.down_revision == "005_create_prediction_knowledge"
    assert trend_topics_revision.doc == "create trend topics table"

    prompt_versions_revision = script.get_revision("007_create_prompt_versions")
    assert prompt_versions_revision.down_revision == "006_create_trend_topics"
    assert prompt_versions_revision.doc == "create prompt versions table"
