
## README - SQL Migrations Review

### Important: SQL Migration Review Required

**Never apply SQL migrations to Supabase without review.**

### Why Review is Required

1. **Security**: Migrations may contain commands that affect data privacy or bypass Row Level Security (RLS) policies
2. **Data Integrity**: Unexpected schema changes can break existing relationships or cause data loss
3. **Supabase Limitations**: Not all PostgreSQL features are supported or may behave differently in Supabase
4. **RLS Policies**: Supabase requires explicit Row Level Security policies on all tables
5. **Migration Order**: Dependencies between migrations must be applied in the correct order

### Review Checklist

- [ ] All tables have RLS policies defined
- [ ] No destructive operations without backup
- [ ] Migration order respects foreign key dependencies
- [ ] UUID columns use proper formatting for Supabase
- [ ] GEOGRAPHY type compatibility verified
- [ ] JSONB columns have appropriate indexes
- [ ] No reserved Supabase identifiers used
- [ ] Policy least-privilege principle applied

### Workflow

1. Draft migration in `supabase/migrations/`
2. **Review by team lead before applying**
3. Test in development Supabase project
4. Verify RLS policies work correctly
5. Apply to production with approval

### Never Commit Raw SQL Without

- [ ] Team review
- [ ] Test execution
- [ ] RLS policy verification
- [ ] Backup confirmation
