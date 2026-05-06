# TARGET_CATALOG = "your_other_catalog"  # uncomment only if not using workshop default

BRONZE_SCHEMA = f"{DB_SCHEMA}_bronze"
SILVER_SCHEMA = f"{DB_SCHEMA}_silver"
GOLD_SCHEMA = f"{DB_SCHEMA}_gold"
# Expected Bronze clone tables (workshop booking app — do not add src_* merge staging names here)
BRONZE_TABLES = ("bookings", "listings", "reviews")
GOLD_TABLES = ("dim_listing", "fact_booking", "fact_review")

print(f"TARGET_CATALOG: {TARGET_CATALOG}")
print(f"BRONZE_SCHEMA:  {BRONZE_SCHEMA}")
print(f"SILVER_SCHEMA:  {SILVER_SCHEMA}")
print(f"GOLD_SCHEMA:    {GOLD_SCHEMA}")
