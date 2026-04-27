# Databricks notebook source
"""Setup Lakebase memory tables for a GenAI agent.

Run as a Databricks notebook or locally with appropriate Lakebase access.
Customize the instance name and embedding endpoint for your project.
"""

# COMMAND ----------

# Parameters — set these for your project
dbutils.widgets.text("lakebase_instance_name", "my-agent-lakebase")
dbutils.widgets.text("agent_name", "my-agent")

instance_name = dbutils.widgets.get("lakebase_instance_name")
agent_name = dbutils.widgets.get("agent_name")

# COMMAND ----------

# Option A: Using the agents.memory helpers (if available in your template)
# These are provided by some Databricks app-templates.
try:
    from agents.memory import ShortTermMemory, LongTermMemory

    print("Setting up short-term memory (CheckpointSaver)...")
    short_term = ShortTermMemory(instance_name=instance_name)
    short_term.setup()
    print("Short-term memory tables created")

    print("Setting up long-term memory (DatabricksStore)...")
    long_term = LongTermMemory(
        instance_name=instance_name,
        embedding_endpoint="databricks-gte-large-en",
        embedding_dims=1024,
    )
    long_term.setup()
    print("Long-term memory tables created")

except ImportError:
    print("agents.memory not available — using direct SQL setup instead")

    # Option B: Direct SQL setup for standard Lakebase tables
    # Adapt this to your schema requirements.
    import os
    from databricks.sdk import WorkspaceClient

    w = WorkspaceClient()
    creds = w.api_client.do(
        "POST",
        "/api/2.0/database/credentials",
        body={"instance_name": instance_name},
    )

    # Connect and create tables
    try:
        import asyncpg
        import asyncio

        async def setup_tables():
            conn = await asyncpg.connect(
                host=creds.get("host"),
                port=int(creds.get("port", 443)),
                user=creds.get("username"),
                password=creds.get("password"),
                database=creds.get("database", "default"),
                ssl="require",
            )
            try:
                await conn.execute("""
                    CREATE SCHEMA IF NOT EXISTS app;

                    CREATE TABLE IF NOT EXISTS app.checkpoints (
                        thread_id TEXT NOT NULL,
                        checkpoint_id TEXT NOT NULL,
                        parent_checkpoint_id TEXT,
                        type TEXT,
                        checkpoint JSONB NOT NULL,
                        metadata JSONB DEFAULT '{}',
                        created_at TIMESTAMPTZ DEFAULT NOW(),
                        PRIMARY KEY (thread_id, checkpoint_id)
                    );

                    CREATE TABLE IF NOT EXISTS app.checkpoint_writes (
                        thread_id TEXT NOT NULL,
                        checkpoint_ns TEXT NOT NULL DEFAULT '',
                        checkpoint_id TEXT NOT NULL,
                        task_id TEXT NOT NULL,
                        idx INTEGER NOT NULL,
                        channel TEXT NOT NULL,
                        type TEXT,
                        blob BYTEA,
                        PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id, task_id, idx)
                    );

                    CREATE TABLE IF NOT EXISTS app.store (
                        prefix TEXT NOT NULL,
                        key TEXT NOT NULL,
                        value JSONB NOT NULL,
                        created_at TIMESTAMPTZ DEFAULT NOW(),
                        updated_at TIMESTAMPTZ DEFAULT NOW(),
                        PRIMARY KEY (prefix, key)
                    );
                """)
                print("Lakebase tables created via direct SQL")
            finally:
                await conn.close()

        asyncio.run(setup_tables())

    except ImportError:
        print("asyncpg not installed. Install with: uv pip install asyncpg")
        print("Then re-run this notebook.")

# COMMAND ----------

print("\n" + "=" * 60)
print("Lakebase memory setup complete!")
print("=" * 60)
print(f"Instance: {instance_name}")
print(f"Agent: {agent_name}")
