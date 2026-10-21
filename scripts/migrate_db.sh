#!/bin/bash
# 数据库迁移脚本 - 初始化所有表

set -e

# 数据库连接信息
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-15432}"
DB_NAME="${DB_NAME:-corn_research}"
DB_USER="${DB_USER:-corn_user}"
DB_PASSWORD="${DB_PASSWORD:-corn_password_2026}"

echo "🌽 Corn Research V2 - Database Migration"
echo "=========================================="
echo "Host: $DB_HOST:$DB_PORT"
echo "Database: $DB_NAME"
echo ""

# 检查PostgreSQL连接
echo "📡 Checking database connection..."
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "SELECT version();" > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ Database connection successful"
else
    echo "❌ Failed to connect to database"
    exit 1
fi

# 执行迁移
echo ""
echo "📝 Running migrations..."

# Migration 001: RAW层表
echo "  [1/2] Creating raw_collection_records table..."
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f migrations/001_create_raw_table.sql > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "  ✅ Migration 001 completed"
else
    echo "  ⚠️  Migration 001 failed (may already exist)"
fi

# Migration 002: STANDARD层表
echo "  [2/2] Creating market_facts_standard table..."
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f migrations/002_create_standard_table.sql > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "  ✅ Migration 002 completed"
else
    echo "  ⚠️  Migration 002 failed (may already exist)"
fi

# 验证表
echo ""
echo "🔍 Verifying tables..."
TABLE_COUNT=$(PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_name IN ('raw_collection_records', 'market_facts_standard');" | tr -d ' ')

if [ "$TABLE_COUNT" = "2" ]; then
    echo "✅ All tables created successfully"
    
    # 显示表信息
    echo ""
    echo "📊 Table Statistics:"
    echo "-------------------"
    
    RAW_COUNT=$(PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -t -c "SELECT COUNT(*) FROM raw_collection_records;" | tr -d ' ')
    echo "  raw_collection_records: $RAW_COUNT rows"
    
    STANDARD_COUNT=$(PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -t -c "SELECT COUNT(*) FROM market_facts_standard;" | tr -d ' ')
    echo "  market_facts_standard: $STANDARD_COUNT rows"
    
    echo ""
    echo "✅ Migration completed successfully!"
else
    echo "⚠️  Expected 2 tables, found $TABLE_COUNT"
    exit 1
fi
