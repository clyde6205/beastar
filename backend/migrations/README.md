# BeAstar.io Database Migrations

## Overview

This directory contains database migration scripts for BeAstar.io. Migrations are numbered sequentially and should be applied in order.

## Migration Files

| File | Description | Status |
|------|-------------|--------|
| `001_initial_schema.sql` | Complete initial schema with all tables, indexes, triggers, and views | ✅ Ready |

## Running Migrations

### Using Supabase Dashboard

1. Go to [Supabase Dashboard](https://app.supabase.com/)
2. Select your project
3. Navigate to **SQL Editor**
4. Open each migration file and run it in order

### Using Supabase CLI

```bash
# Install Supabase CLI
npm install -g supabase

# Link to your project
supabase link --project-ref your-project-ref

# Apply migrations
supabase db push

# Or run specific migration
supabase sql -f backend/migrations/001_initial_schema.sql
```

### Using psql

```bash
# Connect to your database
psql -h your-db-host -U postgres -d your-db-name

# Run migrations
\i backend/migrations/001_initial_schema.sql
```

## Migration Order

Migrations must be applied in numerical order:

1. `001_initial_schema.sql` - Base schema (required)
2. Future migrations will be added as needed

## Creating New Migrations

To create a new migration:

1. Create a new file with the next sequential number (e.g., `002_add_feature.sql`)
2. Include the migration version in the file header
3. Add the migration to the table above
4. Test the migration locally before applying to production

## Migration Template

```sql
-- BeAstar.io - Migration XXX: Description
-- ============================================================
-- Version: XXX
-- Date: YYYY-MM-DD
-- Description: What this migration does
-- Dependencies: Previous migrations that must be run first
-- ============================================================

-- Upgrade SQL (applies changes)
-- Add your SQL here

-- ============================================================
-- Rollback SQL (optional - to undo the migration)
-- Add rollback SQL here if needed
-- ============================================================
```

## Production Considerations

1. **Backup First:** Always backup your database before running migrations
2. **Test First:** Test migrations in a staging environment before production
3. **Downtime:** Some migrations may require downtime - plan accordingly
4. **Rollback Plan:** Have a rollback plan for each migration

## Backup Commands

```bash
# Using Supabase CLI
supabase db dump -f backup.sql

# Using pg_dump
pg_dump -h your-db-host -U postgres -d your-db-name -f backup.sql
```

## Restore Commands

```bash
# Using Supabase CLI
supabase db reset

# Using psql
psql -h your-db-host -U postgres -d your-db-name -f backup.sql
```

## Current Schema Version

The current schema version is tracked in the `schema_migrations` table (if it exists).

## Notes

- All migrations are idempotent (can be run multiple times safely)
- Migrations use `IF NOT EXISTS` to prevent errors on re-run
- The initial schema includes all tables needed for the complete application
- Future migrations will add new features or modify existing structures
