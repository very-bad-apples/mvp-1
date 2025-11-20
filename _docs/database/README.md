# Database Layer Documentation

This directory contains documentation for the Music Video (MV) database layer implementation.

## Files

- **DYNAMODB_SCHEMA.md** - Complete DynamoDB table schema documentation, including:
  - Table structure and key design
  - Item types (Project and Scene)
  - Global Secondary Indexes (GSI)
  - Access patterns and query examples
  - S3 integration patterns

- **DEPLOYMENT_CHECKLIST.md** - Production deployment guide, including:
  - Pre-deployment AWS configuration
  - Environment variable setup
  - Backend and worker deployment steps
  - Post-deployment verification
  - Rollback procedures
  - Production optimization recommendations

## Related Documentation

- **[architecture.md](../architecture.md)** - System architecture overview
- **[key-insights.md](../key-insights.md)** - Key architectural insights and patterns
- **[Backend API Documentation](../../backend/_docs/API_ENDPOINTS.md)** - MV API endpoints reference
- **[Worker Documentation](../../backend/_docs/WORKER.md)** - Worker system for async processing

