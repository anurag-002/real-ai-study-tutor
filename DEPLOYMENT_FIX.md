# Render Deployment Fixes

## Issues Fixed

### 1. Worker Timeout Issues
**Problem:** Gunicorn workers were timing out during startup due to heavy ML library imports.

**Solution:**
- Increased worker timeout to 300 seconds
- Added `--preload` flag to load the application once before forking workers
- Optimized worker configuration with threads

### 2. Database Migration Issues
**Problem:** `no such table: auth_user` error when trying to register users.

**Solution:**
- Added `--run-syncdb` flag to migrations in build.sh and start.sh
- Ensures all Django tables are created properly on first deployment

### 3. DEBUG Variable Not Defined
**Problem:** `NameError: name 'DEBUG' is not defined` in views.py

**Solution:**
- Import `settings` from `django.conf`
- Use `settings.DEBUG` instead of bare `DEBUG` variable

### 4. Static Files Not Found
**Problem:** `/static/index.html` returning 404 errors

**Solution:**
- Build script now runs `collectstatic --no-input --clear`
- This will collect all static files to the proper location

### 5. Duplicate Configuration Files
**Problem:** Both `render.yaml` and `render.yaml.new` exist, causing confusion

**Solution:**
- Removed `render.yaml.new` and `requirements-render.txt`
- Using single `render.yaml` and `requirements.txt`

## Files Modified

1. **backend/views.py**
   - Added `from django.conf import settings`
   - Changed `DEBUG` to `settings.DEBUG`

2. **build.sh**
   - Changed to use `requirements.txt` instead of `requirements-render.txt`
   - Added `--run-syncdb` to migrations

3. **start.sh**
   - Increased timeout to 300 seconds
   - Added `--preload` flag
   - Added threads configuration
   - Added `--max-requests` settings

4. **render.yaml**
   - Updated to use `build.sh` for build command
   - Set DEBUG to False for production
   - Updated Python version to 3.13.4

## Deployment Steps

1. **Delete duplicate files** (if they exist):
   ```bash
   rm render.yaml.new
   rm requirements-render.txt
   ```

2. **Commit and push changes**:
   ```bash
   git add .
   git commit -m "Fix: Deployment issues - timeouts, migrations, DEBUG var"
   git push origin main
   ```

3. **On Render Dashboard**:
   - Go to your service
   - Click "Manual Deploy" > "Clear build cache & deploy"
   - This ensures a clean build with all fixes

4. **After Deployment**:
   - Check logs for successful migration
   - Test user registration
   - Test static file serving

## Testing User Registration

To list all users in the database locally:
```bash
python list_users.py
```

## Environment Variables Needed on Render

Make sure these are set in Render dashboard:
- `DJANGO_SECRET_KEY` (auto-generated)
- `DEBUG` = False
- `GROQ_API_KEY` (your API key)
- `RENDER_EXTERNAL_HOSTNAME` (auto-set by Render)

## Common Issues

### If registration still fails:
1. Check Render logs for database errors
2. Ensure migrations ran successfully during build
3. Try clearing build cache and redeploying

### If static files still 404:
1. Check that `collectstatic` ran in build logs
2. Verify `STATIC_ROOT` and `STATIC_URL` in settings.py
3. Check that WhiteNoise middleware is enabled

### If worker timeouts persist:
1. Consider upgrading to a paid Render plan for more resources
2. The ML libraries (torch, transformers) are very heavy
3. Free tier has limited memory which can cause issues

## Session History Issues

**Problem:** Same session history showing for all users

**Solution:** The session data is currently stored in a SQLite database. Each user should have their own session ID. Check the `db.py` file to ensure:
- Sessions are created with unique IDs per user
- `ensure_session()` properly associates sessions with user IDs
- History queries filter by user_id

This needs to be verified in the database schema and queries.
