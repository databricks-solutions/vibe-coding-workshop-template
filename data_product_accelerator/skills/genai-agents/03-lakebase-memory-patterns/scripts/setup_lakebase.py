# Databricks notebook source
"""Setup Lakebase memory tables for Health Monitor Agent."""

from agents.memory import ShortTermMemory, LongTermMemory

# COMMAND ----------

# Parameters
dbutils.widgets.text("lakebase_instance_name", "health_monitor_lakebase")

instance_name = dbutils.widgets.get("lakebase_instance_name")

# COMMAND ----------

# Setup short-term memory
print("Setting up short-term memory (CheckpointSaver)...")
short_term = ShortTermMemory(instance_name=instance_name)
short_term.setup()
print("✓ Short-term memory tables created")

# COMMAND ----------

# Setup long-term memory
print("Setting up long-term memory (DatabricksStore)...")
long_term = LongTermMemory(
    instance_name=instance_name,
    embedding_endpoint="databricks-gte-large-en",
    embedding_dims=1024
)
long_term.setup()
print("✓ Long-term memory tables created")

# COMMAND ----------

print("\n" + "=" * 60)
print("✅ Lakebase memory setup complete!")
print("=" * 60)
print(f"Instance: {instance_name}")
print(f"Tables created in Unity Catalog")
