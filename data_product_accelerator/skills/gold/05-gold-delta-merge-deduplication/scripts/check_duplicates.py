"""
Utility script for detecting duplicates in Silver tables before merge.

Usage:
    python scripts/check_duplicates.py <catalog> <silver_schema> <silver_table> <business_key>
"""

import sys
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, count

def check_duplicates(
    spark: SparkSession,
    catalog: str,
    silver_schema: str,
    silver_table: str,
    business_key: str
):
    """Check for duplicate business keys in Silver table."""
    full_name = f"{catalog}.{silver_schema}.{silver_table}"
    
    try:
        df = spark.table(full_name)
        
        # Count duplicates
        duplicates = (
            df
            .groupBy(business_key)
            .agg(count("*").alias("count"))
            .filter(col("count") > 1)
        )
        
        dup_count = duplicates.count()
        
        if dup_count > 0:
            print(f"⚠️  Found {dup_count} duplicate business keys in {full_name}")
            print("\nSample duplicates:")
            duplicates.show(10)
            return False
        else:
            print(f"✅ No duplicates found in {full_name}")
            return True
            
    except Exception as e:
        print(f"❌ Error checking duplicates: {e}")
        return False

def main():
    if len(sys.argv) < 5:
        print("Usage: python check_duplicates.py <catalog> <silver_schema> <silver_table> <business_key>")
        sys.exit(1)
    
    catalog = sys.argv[1]
    silver_schema = sys.argv[2]
    silver_table = sys.argv[3]
    business_key = sys.argv[4]
    
    spark = SparkSession.builder.getOrCreate()
    
    success = check_duplicates(spark, catalog, silver_schema, silver_table, business_key)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
