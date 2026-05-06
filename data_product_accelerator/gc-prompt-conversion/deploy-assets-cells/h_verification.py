sep = "=" * 60

def count_rows(catalog: str, schema: str, table: str) -> int:
    return spark.sql(
        f"SELECT COUNT(*) AS c FROM `{catalog}`.`{schema}`.`{table}`"
    ).collect()[0].c

print(sep)
print("VERIFICATION: Bronze (allowlisted tables only; never src_*)")
print(sep)
bronze_counts = {}
for t in BRONZE_TABLES:
    try:
        bronze_counts[t] = count_rows(TARGET_CATALOG, BRONZE_SCHEMA, t)
        print(f"  {t}: {bronze_counts[t]} rows")
    except Exception as e:
        print(f"  {t}: ERROR {e}")
        bronze_counts[t] = -1

print("\n" + sep)
print("VERIFICATION: Silver")
print(sep)
dq_cnt = spark.sql(
    f"SELECT COUNT(*) AS c FROM `{TARGET_CATALOG}`.`{SILVER_SCHEMA}`.`dq_rules`"
).collect()[0].c
print(f"  dq_rules: {dq_cnt} rows")

silver_tables = spark.sql(f"SHOW TABLES IN {TARGET_CATALOG}.{SILVER_SCHEMA}").collect()
silver_streaming = [x.tableName for x in silver_tables if x.tableName.startswith("silver_")]
for t in sorted(silver_streaming):
    c = count_rows(TARGET_CATALOG, SILVER_SCHEMA, t)
    print(f"  {t}: {c} rows")

print("\n" + sep)
print("VERIFICATION: Gold")
print(sep)
gold_counts = {}
for t in GOLD_TABLES:
    try:
        gold_counts[t] = count_rows(TARGET_CATALOG, GOLD_SCHEMA, t)
        print(f"  {t}: {gold_counts[t]} rows")
    except Exception as e:
        print(f"  {t}: ERROR {e}")
        gold_counts[t] = -1

print("\n  Gold constraints:")
constraints = spark.sql(f"""
SELECT table_name, constraint_name, constraint_type
FROM {TARGET_CATALOG}.information_schema.table_constraints
WHERE table_schema = '{GOLD_SCHEMA}'
ORDER BY table_name, constraint_type
""").collect()
for c in constraints:
    print(f"    {c.table_name}: {c.constraint_name} ({c.constraint_type})")

pk_n = len([c for c in constraints if c.constraint_type == "PRIMARY KEY"])
fk_n = len([c for c in constraints if c.constraint_type == "FOREIGN KEY"])

print("\n" + sep)
print("END-TO-END CHECKLIST")
print(sep)
checks = [
    ("Bronze tables present (3 allowlisted)", all(bronze_counts.get(t, -1) >= 0 for t in BRONZE_TABLES)),
    ("Silver streaming tables (>=3 silver_*)", len(silver_streaming) >= 3),
    ("Silver DQ rules populated", dq_cnt > 0),
    ("Gold tables (3 allowlisted)", all(gold_counts.get(t, -1) >= 0 for t in GOLD_TABLES)),
    ("Gold PK constraints (3)", pk_n == 3),
    ("Gold FK constraints (2)", fk_n == 2),
]
all_pass = True
for label, ok in checks:
    status = "PASS" if ok else "FAIL"
    if not ok:
        all_pass = False
    print(f"  {status}  {label}")

print(f"\n{'ALL CHECKS PASSED' if all_pass else 'SOME CHECKS FAILED — inspect rows and constraints above.'}")
