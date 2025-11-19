# Project Documentation

Essential documentation for the AI Video Pipeline MVP-1 project.

---

## 📚 Core Documentation

### [Architecture](architecture.md)
Complete system architecture including:
- Technology stack (Next.js, FastAPI, DynamoDB, S3, Redis)
- Database design (DynamoDB single-table pattern)
- Storage architecture (S3 with presigned URLs)
- API endpoints and data flow
- Worker architecture for async processing
- Deployment considerations

**Read this first** to understand the overall system design.

### [Key Insights](key-insights.md)
Extracted wisdom from implementation experience:
- Pipeline architecture principles (script-first approach)
- Hardcoded template strategy
- Cost optimization tactics ($1.46/video target)
- Performance targets (< 8 min generation time)
- Technical patterns worth keeping
- Security considerations

**Quick reference** for important architectural decisions and lessons learned.

### [Best Practices](best-practices.md)
MVP development philosophy and guidelines:
- Code review standards for MVP phase
- What to approve vs. block
- Development philosophy (speed over perfection)
- Testing priorities
- When to optimize

**Essential reading** for maintaining development velocity while ensuring quality.

---

## 🔧 Component Documentation

### Backend
- [Backend Overview](backend/README.md) - Component organization and setup
- [Scripts Guide](backend/scripts-README.md) - Utility scripts documentation
- [Tests Guide](backend/tests-README.md) - Test suite organization

### Database
- [Schema Documentation](database/DYNAMODB_SCHEMA.md) - DynamoDB table design
- [Deployment Checklist](database/DEPLOYMENT_CHECKLIST.md) - Production setup steps
- [Database Layer Overview](database/README.md) - Implementation details

---

## 🗂️ Documentation Organization

```
_docs/
├── README.md                   # This file
├── architecture.md             # System architecture (44KB)
├── key-insights.md             # Extracted lessons (11KB)
├── best-practices.md           # MVP development guidelines
├── backend/                    # Backend component docs
│   ├── README.md
│   ├── scripts-README.md
│   └── tests-README.md
└── database/                   # Database layer docs
    ├── DYNAMODB_SCHEMA.md
    ├── DEPLOYMENT_CHECKLIST.md
    └── README.md
```

**Additional Backend Docs**: See [`backend/_docs/`](../backend/_docs/) for:
- `API_ENDPOINTS.md` - Complete API reference
- `WORKER.md` - Worker system documentation

---

## 🚀 Quick Start Paths

### New Developer Onboarding
1. Read [Architecture](architecture.md) - Understand the system
2. Read [Best Practices](best-practices.md) - Learn development approach
3. Check [Backend README](backend/README.md) - Set up local environment
4. Review [Database Schema](database/DYNAMODB_SCHEMA.md) - Understand data model

### Understanding a Component
- **API Endpoints**: [`backend/_docs/API_ENDPOINTS.md`](../backend/_docs/API_ENDPOINTS.md)
- **Worker System**: [`backend/_docs/WORKER.md`](../backend/_docs/WORKER.md)
- **Database Setup**: [Database README](database/README.md)

### Deploying to Production
1. Follow [Deployment Checklist](database/DEPLOYMENT_CHECKLIST.md)
2. Review [Architecture: Deployment](architecture.md#deployment-architecture)
3. Check [Key Insights: Security](key-insights.md#security--production-readiness)

---

## 📝 Documentation Standards

### What Belongs in `_docs/`
✅ System architecture and design
✅ Active reference material
✅ Development guidelines
✅ Component overviews
✅ Deployment guides

### What Doesn't Belong Here
❌ Task summaries (use Task Master)
❌ Testing notes (phase-specific)
❌ Historical/archived content
❌ Personal notes and workflows

---

## 🔄 Keeping Documentation Updated

When making significant changes:
- Update [Architecture](architecture.md) if system design changes
- Update [Key Insights](key-insights.md) if you discover important patterns
- Update component READMEs when adding major features
- Keep [Best Practices](best-practices.md) current with team agreements

---

## 📞 Getting Help

- **Architecture Questions**: Check [architecture.md](architecture.md)
- **Implementation Questions**: Check [key-insights.md](key-insights.md)
- **Setup Issues**: Check component READMEs in [backend/](backend/) or [database/](database/)
- **API Reference**: See [`backend/_docs/API_ENDPOINTS.md`](../backend/_docs/API_ENDPOINTS.md)

---

**Last Updated**: 2025-11-19
