# Mobile App Integration Checklist

## API Endpoints Verification

### Authentication
- [ ] API key authentication works on `/v1/*` endpoints
- [ ] Invalid API key returns 401
- [ ] Missing API key returns 401
- [ ] API key rate limiting enforced

### Student Data
- [ ] `GET /v1/students` returns student list for institution
- [ ] Response includes student ID, name, reg_number
- [ ] Photo URLs accessible from Supabase Storage
- [ ] Student filtering by institution works

### Attendance Recording
- [ ] `POST /v1/attendance` accepts attendance records
- [ ] Required fields: student_id, session_id, confidence
- [ ] Optional: anti_spoof_passed, status
- [ ] Returns confirmation with record ID

### Session Management
- [ ] `GET /v1/sessions` returns active sessions
- [ ] Sessions filtered by institution
- [ ] Session status (active/completed) included

## Face Recognition Flow

### 1. App Startup
- [ ] App fetches API key from secure storage
- [ ] Health check confirms backend connectivity
- [ ] Download student photos for offline use

### 2. Session Start
- [ ] Fetch active sessions for institution
- [ ] Select or create session
- [ ] Load enrolled student photos

### 3. Face Detection
- [ ] Camera captures face image
- [ ] Local face detection runs
- [ ] Generate face embedding locally

### 4. Face Matching
- [ ] Compare against enrolled students
- [ ] Confidence score calculated
- [ ] Anti-spoofing check (liveness detection)

### 5. Attendance Submission
- [ ] POST to `/v1/attendance` with results
- [ ] Handle network failures (queue for retry)
- [ ] Show confirmation to user

## Testing Scenarios

### Happy Path
```bash
# 1. Get students
curl -H "X-API-Key: YOUR_KEY" https://your-app/v1/students

# 2. Get active session
curl -H "X-API-Key: YOUR_KEY" https://your-app/v1/sessions

# 3. Record attendance
curl -X POST https://your-app/v1/attendance \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "student_id": "student-123",
    "session_id": "session-uuid",
    "confidence": 0.95,
    "anti_spoof_passed": true,
    "status": "present"
  }'
```

### Error Cases
- [ ] Expired API key
- [ ] Invalid student_id
- [ ] Invalid session_id
- [ ] Low confidence score (<0.7)
- [ ] Network timeout handling
- [ ] Offline mode queue

## Performance

### Response Times
- [ ] `/v1/students` responds in <500ms
- [ ] `/v1/attendance` responds in <200ms
- [ ] Photo downloads optimized (thumbnails?)

### Data Transfer
- [ ] Student list payload size reasonable
- [ ] Photos compressed appropriately
- [ ] Pagination for large student lists

## Security

### API Key Management
- [ ] Keys stored securely on device (Keychain/Keystore)
- [ ] Keys not logged or exposed
- [ ] Key rotation supported

### Data Protection
- [ ] HTTPS enforced
- [ ] Photos not cached insecurely
- [ ] Face embeddings not stored permanently

## Offline Support

### Sync Strategy
- [ ] Download all students on WiFi
- [ ] Queue attendance when offline
- [ ] Auto-sync when connection restored
- [ ] Conflict resolution (duplicate submissions)

## Edge Cases

### Billing Limits
- [ ] Institution expired subscription blocks operations
- [ ] Grace period allows limited access
- [ ] Student limit exceeded prevents new enrollments

### Data Issues
- [ ] Missing student photo handled gracefully
- [ ] Corrupted photo skipped
- [ ] Duplicate attendance prevented
- [ ] Invalid session ID rejected

## Monitoring

### Metrics to Track
- [ ] API success rate per endpoint
- [ ] Average confidence scores
- [ ] Anti-spoof pass rate
- [ ] Attendance submission failures
- [ ] Network retry frequency

### Logs
- [ ] Backend logs attendance submissions
- [ ] Failed authentications logged
- [ ] Unusual patterns flagged (Sentry)

## Deployment

### APK Release
- [ ] Update API base URL for production
- [ ] Bundle correct API keys per environment
- [ ] Version compatibility with backend

### Backend Updates
- [ ] Deploy latest code to DigitalOcean
- [ ] Run production verification script
- [ ] Monitor error rates post-deployment

---

**Status**: Ready for mobile team integration  
**Backend Version**: Phase 2 Billing + Mobile APIs  
**Last Updated**: 2026-06-04
