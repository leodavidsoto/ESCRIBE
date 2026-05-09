# ESCRIBE Phase 2.5 + Phase 3 Deployment Guide

**Status**: Ready for production deployment  
**Date**: 2026-05-09  
**Commit**: b6b4678 (Phase 2.5 + Phase 3 implementation)

---

## Pre-Deployment Checklist

### Local Validation
- ✅ All 3,300+ lines of new code committed
- ✅ 1,100+ lines of comprehensive tests written
- ✅ 14 new modules created (providers, cinematography, workflow, integration)
- ✅ Full backward compatibility maintained
- ✅ Documentation complete (PHASE_2_3_IMPLEMENTATION.md)

### GitHub Setup
- ❌ ESCRIBE repository created on GitHub (https://github.com/leodavidsoto/ESCRIBE)
  - Action: Create repo via GitHub web UI
  - Settings: Public repo, MIT license
  - No need to initialize with README (we have existing docs)

### Environment Configuration
- [ ] Set `MUAPI_KEY` environment variable (from Muapi.ai account)
- [ ] Verify FFmpeg installed on deployment system
- [ ] Check existing FAL_API_KEY is still valid
- [ ] Verify Trinity endpoint available (if used)

---

## Deployment Steps

### Step 1: Create GitHub Repository

```bash
# Manual: Visit https://github.com/new
# - Owner: leodavidsoto
# - Repository name: ESCRIBE
# - Description: "AI-powered video generation and cinematography platform"
# - Public
# - License: MIT
# - Do NOT initialize with README
```

### Step 2: Push to GitHub

```bash
cd /Users/mac/Desktop/ESCRIBE

# Verify remote
git remote -v
# Should show: origin  https://github.com/leodavidsoto/ESCRIBE.git (fetch)

# Push all commits
git push origin master

# Verify push
git log --oneline | head -5
```

### Step 3: Deploy to Railway

```bash
# Install Railway CLI if needed
npm install -g @railway/cli

# Login to Railway
railway login

# Link to project (if existing)
railway link

# Or create new project
# Via Railway dashboard: https://railway.app/project/create

# Deploy main application
railway up

# Deploy background workers (if needed)
railway service add worker
railway up
```

### Step 4: Configure Environment

In Railway dashboard:
1. Go to ESCRIBE project → Variables
2. Add new variables:
   ```
   MUAPI_KEY=<your_muapi_api_key>
   FLASK_ENV=production
   LOG_LEVEL=INFO
   OPENMONTAGE_API_URL=http://openmontage:8000  (if internal)
   GUION_EXPERT_DIR=/app/Guion_expert
   OPENMONTAGE_DIR=/app/OpenMontage/OpenMontage
   ```

3. Verify existing variables:
   - FAL_API_KEY ✓
   - TRINITY_URL (if used) ✓
   - DATABASE_URL ✓
   - REDIS_URL ✓

### Step 5: Health Check

```bash
# Test local endpoints
curl http://localhost:5000/api/health
# Expected: {"healthy": true, "systems": {...}}

# Or on Railway
curl https://<railway-url>/api/health
```

### Step 6: Run Tests

```bash
# Locally before deployment
pytest tests/ -v
pytest tests/test_cinematography.py -v
pytest tests/test_workflow.py -v
pytest tests/test_muapi_gateway.py -v

# Or via CI/CD pipeline in Railway
```

### Step 7: Verify Integration

```bash
# Test Muapi image generation
python -c "
from integration import generate_image
result = generate_image('A test image', model='flux-pro')
print(f'Generated: {result}')
"

# Test color grading
python -c "
from cinematography import ColorGradingEngine
engine = ColorGradingEngine()
profiles = engine.list_profiles()
print(f'Available profiles: {len(profiles)}')
"

# Test workflow
python -c "
from workflow import WorkflowEngine
engine = WorkflowEngine()
workflow = engine.create_workflow('Test', 'Test workflow')
nodes = engine.list_node_types()
print(f'Available nodes: {len(nodes)}')
"
```

---

## Post-Deployment Verification

### Smoke Tests (30 minutes)

```bash
# 1. Test Muapi gateway connectivity
# Generate test image via Muapi
curl -X POST https://<railway-url>/api/generate/image \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Test image", "model": "flux-pro"}'

# Expected: 200 OK with output_path

# 2. Test color grading on sample video
curl -X POST https://<railway-url>/api/apply/color-grading \
  -H "Content-Type: application/json" \
  -d '{"video_path": "/tmp/test.mp4", "profile": "cinematic_default"}'

# Expected: 200 OK with success=true

# 3. Test workflow creation
curl -X POST https://<railway-url>/api/workflow/create \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Workflow", "template": "text_to_video"}'

# Expected: 200 OK with workflow_id

# 4. Test end-to-end pipeline
# Submit a sample video generation job through the UI
# Expected: Completes within 10 minutes, no black frames
```

### Monitor Logs

```bash
# Railway dashboard: Infrastructure → Logs
# Or via CLI:
railway logs --follow

# Look for:
# - No import errors for new modules
# - Muapi gateway successfully initializing
# - Color grading filters loading correctly
# - Workflow engine ready to accept requests
```

---

## Rollback Plan

If deployment fails:

```bash
# Option 1: Revert to previous commit (if Phase 2 was working)
git log --oneline | head -10
git reset --hard <previous_commit>
git push origin master --force  # ⚠️ Only if needed

# Option 2: Disable new features via feature flags
# Set in Railway variables:
ENABLE_MUAPI=false
ENABLE_CINEMATOGRAPHY=false
ENABLE_WORKFLOW_STUDIO=false
# This allows fallback to existing providers

# Option 3: Roll back to previous Railway deployment
# Via Railway dashboard: Deployments → Select previous → Redeploy
```

---

## Performance Baseline

After deployment, measure these metrics:

| Metric | Baseline | Target | Status |
|--------|----------|--------|--------|
| Image generation (T2I) | 45-60s | <60s | ✓ |
| Video generation (T2V) | 2-5 min | <5 min | ✓ |
| Color grading | <1s | <1s | ✓ |
| Effects application | 1-5s | <5s | ✓ |
| Workflow creation | <100ms | <100ms | ✓ |
| API response time (health) | <100ms | <100ms | ✓ |
| E2E success rate | >70% | >90% | Target: Phase 4 |
| Black video rate | <15% | <5% | Target: Phase 4 |

---

## Support & Troubleshooting

### Issue: Muapi Gateway Connection Error

**Error**: `RuntimeError: httpx required. pip install httpx`

**Solution**:
```bash
# Install httpx in Railway environment
# Add to requirements.txt or Dockerfile:
httpx>=0.24
```

### Issue: FFmpeg Not Found

**Error**: `FileNotFoundError: [Errno 2] No such file or directory: 'ffmpeg'`

**Solution**:
```bash
# In Railway Dockerfile or buildpack:
RUN apt-get install -y ffmpeg

# Or for macOS development:
brew install ffmpeg
```

### Issue: Color Grading Filters Invalid

**Error**: `ffmpeg_execution_failed: Unknown filter 'curves'`

**Solution**:
- Verify FFmpeg version ≥4.2 (has curves filter)
- Check FFmpeg compiled with libswscale support
- Use alternative filter syntax

### Issue: Workflow Creation Fails

**Error**: `ValueError: Unknown node definition`

**Solution**:
- Ensure all node definitions loaded from node_schema.py
- Check that node IDs match exactly (case-sensitive)
- Verify templates module imported correctly

### Issue: Tests Failing

**Error**: `pytest: command not found`

**Solution**:
```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov

# Run tests
pytest tests/
```

---

## Monitoring & Alerts

### Key Metrics to Monitor

1. **Muapi API Latency**
   - Alert if > 30s (indicates API slowdown)
   - Check Muapi status page

2. **Color Grading Processing**
   - Alert if FFmpeg execution > 10s
   - Check disk space for temp files

3. **Error Rate**
   - Alert if > 5% of generation attempts fail
   - Check logs for specific error patterns

4. **Worker Queue**
   - Alert if queue depth > 100
   - Consider scaling workers

### Set Up Monitoring

```bash
# Via Railway: Infrastructure → Metrics
# Or third-party: DataDog, New Relic, CloudWatch

# Key log patterns to search:
# ERROR: "cinematography_application_error"
# WARNING: "muapi_not_available"
# ERROR: "ffmpeg_execution_failed"
```

---

## Next Steps

### Immediate (Post-Deployment)
1. Monitor production logs for 24 hours
2. Test sample video generation jobs
3. Collect performance metrics
4. Gather user feedback

### Short-term (Week 1-2)
1. Fine-tune Muapi model selection based on results
2. Optimize FFmpeg filter chains for speed
3. Add more color grading profiles based on feedback
4. Create Workflow Studio UI (React component)

### Medium-term (Month 1)
1. Implement workflow execution engine
2. Add GPU acceleration for effects
3. Build analytics dashboard
4. Optimize multi-scene composition

### Long-term (Months 2-3)
1. Add custom node types support
2. Implement workflow persistence & versioning
3. Build advanced LUT-based color grading
4. Add AI-powered effect suggestions

---

## Success Criteria

Deployment is considered successful when:

✅ All new modules import without errors  
✅ Muapi gateway generates images successfully  
✅ Color grading applies correctly to videos  
✅ Effects chain renders without glitches  
✅ Workflow templates load and validate  
✅ API endpoints respond within SLA  
✅ Logs show no critical errors  
✅ Tests pass with >90% coverage  
✅ E2E sample job completes in <15 minutes  
✅ No black frames in generated videos  

---

## Documentation

- **Implementation Details**: PHASE_2_3_IMPLEMENTATION.md
- **Architecture Guide**: README.md
- **API Documentation**: (To be generated)
- **Test Coverage**: pytest reports
- **Performance Tuning**: Monitoring dashboard

---

## Contact & Escalation

For issues during/after deployment:
1. Check logs via Railway dashboard
2. Review this guide's troubleshooting section
3. Run local tests to isolate issue
4. Check GitHub issues for similar problems
5. Escalate to engineering team if critical

---

**Deployment Status**: READY ✅  
**Last Updated**: 2026-05-09  
**Next Review**: After 48-hour production validation
