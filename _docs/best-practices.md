# Best Practices - MVP Phase

## 🚀 Development Philosophy: Speed Over Perfection

**Current Phase: MVP-1 - Week 1**
**Priority: Ship working features > Perfect code**

---

## Code Review Standards for MVP

### ✅ APPROVE IF:

- Code works correctly for the happy path
- No critical security vulnerabilities (SQL injection, XSS, exposed secrets)
- No data loss or corruption risks
- Basic error handling exists
- Types are present (no excessive `any` in TypeScript)
- Functions/methods have clear purpose
- No breaking changes to existing functionality

### ⚠️ NON-BLOCKING (Approve with recommendations):

- Missing edge case handling
- Could be more DRY (Don't Repeat Yourself)
- Performance optimizations needed
- Additional test coverage desired
- Documentation could be better
- Code style inconsistencies (non-critical)
- TODO comments for future improvements
- Could use better abstractions
- Missing comprehensive input validation
- Logging could be more detailed
- Error messages could be more specific

### 🚫 BLOCK ONLY IF:

- **Breaks existing functionality**
- **Exposes secrets or credentials** (API keys, passwords, tokens)
- **Creates data corruption risk** (data loss, inconsistent state)
- **Violates security best practices** (OWASP Top 10 vulnerabilities)
- **Missing critical error handling** that causes application crashes
- **Introduces memory leaks** or severe performance degradation
- **Hardcoded production values** that should be environment variables

---

## MVP Philosophy

We're building to **validate the concept**. Focus on:

1. **Working features shipped quickly**
2. **Minimum viable quality** (good enough for testing)
3. **Refactor in Phase 2** based on learnings from real usage

### What We're Optimizing For:

- ✅ Fast iteration cycles
- ✅ Learning and validation
- ✅ Working end-to-end functionality
- ✅ Core happy path implementation
- ✅ Basic error handling (graceful failures)

### What We're NOT Optimizing For Yet:

- ⏸️ Perfect abstractions
- ⏸️ Comprehensive test coverage (focus on critical paths only)
- ⏸️ Performance optimization (unless critical)
- ⏸️ Edge case handling (document as TODOs)
- ⏸️ Extensive documentation (inline comments for complex logic only)
- ⏸️ Code reusability across projects
- ⏸️ Scalability beyond MVP needs

---

## Technical Debt: Acceptable vs. Unacceptable

### ✅ Acceptable Technical Debt (Fix in Phase 2):

- Duplicated code across components
- Missing unit tests (integration tests preferred for MVP)
- Incomplete error messages
- Lack of input sanitization for non-critical fields
- Missing JSDoc/docstrings
- Console.log/print statements for debugging
- Hardcoded values that aren't secrets (can be constants)
- Repetitive validation logic
- Missing optimizations (caching, batching, etc.)

### 🚫 Unacceptable Technical Debt (Fix NOW):

- Exposed credentials or API keys
- No error handling on critical operations (DB writes, API calls)
- Unvalidated user input that could cause crashes
- SQL injection or NoSQL injection vulnerabilities
- Missing authentication on protected endpoints (if auth is implemented)
- File upload vulnerabilities (path traversal, unrestricted file types)
- Race conditions that cause data corruption
- Memory leaks in long-running processes

---

## Technology-Specific Guidelines

### Python (Backend)

**Approve if:**
- Type hints on function signatures
- Try/except on external calls (DB, API, file I/O)
- Pydantic models for request/response validation
- No bare `except:` clauses (at least `except Exception`)

**Can wait:**
- Comprehensive type hints on internal variables
- Custom exception classes
- Extensive logging
- Unit tests for every function

### TypeScript (Frontend)

**Approve if:**
- No `any` types (use `unknown` if truly unknown)
- Props interfaces for components
- Basic error handling on API calls
- No unused imports/variables

**Can wait:**
- Perfect prop naming conventions
- Comprehensive test coverage
- Performance optimizations (memoization, lazy loading)
- Accessibility enhancements (ARIA labels, keyboard nav)

### DynamoDB

**Approve if:**
- Correct PK/SK structure
- No hard-coded table names (use config)
- Error handling on queries/updates
- GSI queries don't scan entire table

**Can wait:**
- Batch operations for efficiency
- Conditional updates for concurrency
- Read/write capacity optimization
- Comprehensive TTL strategies

### S3

**Approve if:**
- No public ACLs (use presigned URLs)
- File type validation on uploads
- Error handling on upload/download
- Proper cleanup of temp files

**Can wait:**
- Multipart uploads for large files
- Automatic retry logic
- CloudFront CDN integration
- Lifecycle policies beyond basics

---

## Commit Message Standards (Lightweight)

Use conventional commits format, but keep it simple:

```
feat: add DynamoDB project creation endpoint
fix: handle missing S3 key error
refactor: extract S3 service to separate file
docs: update architecture diagram
test: add integration test for scene creation
```

**Good enough for MVP:**
- Clear subject line (50 chars max preferred)
- Body optional for obvious changes
- Reference task IDs if using task tracker

**Not required for MVP:**
- Breaking change footers
- Detailed multi-paragraph explanations
- Issue references (unless specifically tracking)

---

## When to Ask Questions vs. Proceed

### Ask First:

- Architecture decisions (new patterns, new services)
- Breaking changes to existing APIs
- Adding new dependencies
- Security-related implementations
- Data model changes

### Proceed with Confidence:

- Bug fixes
- Adding new endpoints following existing patterns
- Refactoring within a single file
- Adding validation logic
- Improving error messages
- Documentation updates

---

## Testing Strategy for MVP

### Required:

- **Integration tests** for critical user flows (project creation → video generation → retrieval)
- **Manual testing** of happy path after each feature
- **Smoke tests** for deployment

### Optional (Phase 2):

- Unit tests for utility functions
- Edge case testing
- Load testing
- Security penetration testing
- Comprehensive E2E test suite

---

## Code Review Response Times

**Goal: Unblock within 15 minutes during work hours**

- Most commits should be approved quickly
- If blocking issues found, provide specific fix suggestions
- If recommendations only, approve immediately with notes

---

## Remember:

> **"Perfect is the enemy of done."**
> — Voltaire

We're building an MVP to validate the concept. Code quality matters, but **shipping working features matters more**. Refactor based on real user feedback, not theoretical perfection.

---

**Last Updated:** 2025-11-17
**Phase:** MVP-1 Database Layer Implementation
**Review Philosophy:** Speed-first, quality-aware
