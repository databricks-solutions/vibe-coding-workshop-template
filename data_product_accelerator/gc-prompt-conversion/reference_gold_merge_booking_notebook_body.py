# Reference: notebook BODY only (pass to make_job_notebook(body) from workshop-variables).
# Matches Silver booking workshop: string listing/review ids, optional empty bookings,
# YAML-only fee columns on dim_listing, YAML-only columns on fact_booking.
# Sync path in workspace: .../src/{DB_SCHEMA}_gold/gold_merge (no .py extension).

# COMMAND ----------
GOLD_SCHEMA = DB_SCHEMA + "_gold"
SILVER_SCHEMA = DB_SCHEMA + "_silver"

# COMMAND ----------
# 1. dim_date
from pyspark.sql.functions import (
    col,
    lit,
    expr,
    current_timestamp,
    date_format,
    dayofmonth,
    dayofweek,
    month,
    quarter,
    year,
    weekofyear,
    when,
    regexp_extract,
)

start_date = "2020-01-01"
end_date = "2030-12-31"

date_df = (
    spark.sql(
        f"SELECT explode(sequence(to_date('{start_date}'), to_date('{end_date}'), interval 1 day)) as full_date"
    )
    .withColumn("date_key", expr("CAST(date_format(full_date, 'yyyyMMdd') AS INT)"))
    .withColumn("year", year("full_date"))
    .withColumn("quarter", quarter("full_date"))
    .withColumn("month", month("full_date"))
    .withColumn("month_name", date_format("full_date", "MMMM"))
    .withColumn("day_of_month", dayofmonth("full_date"))
    .withColumn("day_of_week", dayofweek("full_date"))
    .withColumn("day_name", date_format("full_date", "EEEE"))
    .withColumn("is_weekend", when(dayofweek("full_date").isin(1, 7), lit(True)).otherwise(lit(False)))
    .withColumn("week_of_year", weekofyear("full_date"))
    .select(
        "date_key",
        "full_date",
        "year",
        "quarter",
        "month",
        "month_name",
        "day_of_month",
        "day_of_week",
        "day_name",
        "is_weekend",
        "week_of_year",
    )
)

date_df.write.format("delta").mode("overwrite").saveAsTable(
    f"`{TARGET_CATALOG}`.`{GOLD_SCHEMA}`.`dim_date`"
)

# COMMAND ----------
# 2. dim_listing — add YAML-only columns as NULL before MERGE (Silver has no cleaning_fee, etc.)
silver_listings = spark.table(
    f"`{TARGET_CATALOG}`.`{SILVER_SCHEMA}`.`silver_listings`"
).dropDuplicates(["id"])

source_df = (
    silver_listings.withColumn("listing_key", col("id").cast("bigint"))
    .withColumn("listing_id", col("id").cast("int"))
    .withColumn("latitude", col("lat"))
    .withColumn("longitude", col("lng"))
    .withColumn("cleaning_fee", lit(None).cast("decimal(10,2)"))
    .withColumn("service_fee_rate", lit(None).cast("decimal(5,4)"))
    .withColumn("tax_rate", lit(None).cast("decimal(5,4)"))
    .withColumn("listing_created_at", col("created_at"))
    .withColumn("gold_loaded_at", current_timestamp())
    .select(
        "listing_key",
        "listing_id",
        "title",
        "description",
        "location",
        "city",
        "state",
        "latitude",
        "longitude",
        "property_type",
        "bedrooms",
        "bathrooms",
        "max_guests",
        "price_per_night",
        "cleaning_fee",
        "service_fee_rate",
        "tax_rate",
        "rating",
        "review_count",
        "host_name",
        "listing_created_at",
        "gold_loaded_at",
    )
)

source_df.printSchema()
source_df.createOrReplaceTempView("src_dim_listing")

spark.sql(
    f"""
MERGE INTO `{TARGET_CATALOG}`.`{GOLD_SCHEMA}`.`dim_listing` AS tgt
USING src_dim_listing AS src
ON tgt.listing_key = src.listing_key
WHEN MATCHED THEN UPDATE SET *
WHEN NOT MATCHED THEN INSERT *
"""
)

# COMMAND ----------
# 3. fact_booking — guard empty Silver; NULL placeholders for YAML-only columns
silver_bookings = spark.table(
    f"`{TARGET_CATALOG}`.`{SILVER_SCHEMA}`.`silver_bookings`"
).dropDuplicates(["id"])

if silver_bookings.count() == 0:
    print("fact_booking: 0 Silver rows — skip MERGE")
else:
    booking_src = (
        silver_bookings.withColumn("booking_key", col("id").cast("bigint"))
        .withColumn("booking_id", col("id").cast("bigint"))
        .withColumn("reference_number", lit(None).cast("string"))
        .withColumn("listing_key", col("listing_id").cast("bigint"))
        .withColumn("check_in_date_key", expr("CAST(date_format(check_in, 'yyyyMMdd') AS INT)"))
        .withColumn("check_out_date_key", expr("CAST(date_format(check_out, 'yyyyMMdd') AS INT)"))
        .withColumn("nightly_rate", lit(None).cast("decimal(10,2)"))
        .withColumn("nights", lit(None).cast("int"))
        .withColumn("cleaning_fee", lit(None).cast("decimal(10,2)"))
        .withColumn("service_fee", lit(None).cast("decimal(10,2)"))
        .withColumn("taxes", lit(None).cast("decimal(10,2)"))
        .withColumn("discount", lit(None).cast("decimal(10,2)"))
        .withColumn("total_revenue", col("total_price"))
        .withColumn("coupon_code", lit(None).cast("string"))
        .withColumn("booking_created_at", col("created_at"))
        .withColumn("gold_loaded_at", current_timestamp())
        .select(
            "booking_key",
            "booking_id",
            "reference_number",
            "listing_key",
            "check_in_date_key",
            "check_out_date_key",
            "guest_name",
            "guest_email",
            "guests",
            "nightly_rate",
            "nights",
            "cleaning_fee",
            "service_fee",
            "taxes",
            "discount",
            "total_revenue",
            "coupon_code",
            "booking_created_at",
            "gold_loaded_at",
        )
    )
    booking_src.printSchema()
    booking_src.createOrReplaceTempView("src_fact_booking")
    spark.sql(
        f"""
MERGE INTO `{TARGET_CATALOG}`.`{GOLD_SCHEMA}`.`fact_booking` AS tgt
USING src_fact_booking AS src
ON tgt.booking_key = src.booking_key
WHEN MATCHED THEN UPDATE SET *
WHEN NOT MATCHED THEN INSERT *
"""
    )

# COMMAND ----------
# 4. fact_review — ids like "r1" need regexp_extract before bigint cast
silver_reviews = spark.table(
    f"`{TARGET_CATALOG}`.`{SILVER_SCHEMA}`.`silver_reviews`"
).dropDuplicates(["id"])

review_src = (
    silver_reviews.withColumn("review_key", regexp_extract(col("id"), r"(\d+)", 1).cast("bigint"))
    .withColumn("review_id", regexp_extract(col("id"), r"(\d+)", 1).cast("int"))
    .withColumn("listing_key", col("listing_id").cast("bigint"))
    .withColumn("review_date_key", expr("CAST(date_format(review_date, 'yyyyMMdd') AS INT)"))
    .withColumn("reviewer_name", col("guest_name"))
    .withColumn("rating", col("rating").cast("decimal(3,1)"))
    .withColumn("review_created_at", col("created_at"))
    .withColumn("gold_loaded_at", current_timestamp())
    .select(
        "review_key",
        "review_id",
        "listing_key",
        "review_date_key",
        "reviewer_name",
        "rating",
        "comment",
        "review_date",
        "review_created_at",
        "gold_loaded_at",
    )
)

review_src.printSchema()
review_src.createOrReplaceTempView("src_fact_review")

spark.sql(
    f"""
MERGE INTO `{TARGET_CATALOG}`.`{GOLD_SCHEMA}`.`fact_review` AS tgt
USING src_fact_review AS src
ON tgt.review_key = src.review_key
WHEN MATCHED THEN UPDATE SET *
WHEN NOT MATCHED THEN INSERT *
"""
)

# COMMAND ----------
print("\n=== Gold Layer Population Summary ===")
for tbl in ["dim_date", "dim_listing", "fact_booking", "fact_review"]:
    cnt = spark.sql(
        f"SELECT COUNT(*) as cnt FROM `{TARGET_CATALOG}`.`{GOLD_SCHEMA}`.`{tbl}`"
    ).collect()[0].cnt
    print(f"  {tbl}: {cnt} rows")
