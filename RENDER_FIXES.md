# Render Deployment Fixes Applied

## Issues Found

Based on your error logs, there were three critical issues:

1. **Python 3.13 Incompatibility** - Render was using Python 3.13.4 instead of 3.11, causing compatibility issues with ML libraries (scipy, sympy, torch)
2. **Worker Timeout** - Gunicorn workers were timing out (30 seconds) while loading sentence-transformers at import time
3. **Memory Issues** - Workers were being killed with "Perhaps out of memory?" messages

## Fixes Applied

### 1. Fixed Python Version
**Files Changed:** `render.yaml`, `runtime.txt`

- Set `PYTHON_VERSION: 3.11.9` in environment variables
- Updated `runtime.txt` to `python-3.11.9`
- Python 3.11 is the last stable version with full ML library support

### 2. Lazy-Loading ML Models
**File Changed:** `backend/rag.py`

Changed from eager loading:
```python
# OLD - Loaded at import time, blocking worker startup
from sentence_transformers import SentenceTransformer
EMBEDDING_MODEL = SentenceTransformer('all-MiniLM-L6-v2')
```

To lazy loading:
```python
# NEW - Loaded on first use
def _get_embedding_model():
    global EMBEDDING_MODEL
    if EMBEDDING_MODEL is None:
        from sentence_transformers import SentenceTransformer
        EMBEDDING_MODEL = SentenceTransformer('all-MiniLM-L6-v2')
    return EMBEDDING_MODEL
```

**Why:** This prevents the 30+ second import from blocking gunicorn worker startup, which was causing timeout errors.

### 3. Optimized Gunicorn Configuration
**File Changed:** `render.yaml`

Changed start command from:
```bash
gunicorn backend.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 120
```

To:
```bash
gunicorn backend.wsgi:application --bind 0.0.0.0:$PORT --workers 1 --timeout 300 --preload
```

**Changes:**
- `--workers 1` - Reduced from 2 to save memory on free tier
- `--timeout 300` - Increased from 120 to allow more time for first request
- `--preload` - Load application before forking workers for better memory efficiency

### 4. Fixed Static Files Warning
**Already configured:** WhiteNoise middleware and STATIC_ROOT in settings.py
- The "No directory at staticfiles/" warning is harmless - it appears before collectstatic runs
- After first request, static files are properly served

## What to Do Next

1. **Commit and push these changes:**
   ```bash
   git add .
   git commit -m "Fix Render deployment: Python 3.11, lazy-load ML models, optimize gunicorn"
   git push
   ```

2. **In Render Dashboard:**
   - Go to your service
   - Check Environment tab and ensure `PYTHON_VERSION` is set to `3.11.9`
   - Trigger a manual deploy or wait for auto-deploy
   - Set your `GROQ_API_KEY` environment variable if not already set

3. **Monitor the deployment:**
   - Build should complete in 5-10 minutes
   - Watch logs for "Listening at: http://0.0.0.0:10000"
   - First request will take 10-20 seconds (loading ML models)
   - Subsequent requests will be fast

## Expected Behavior After Fix

### During Startup:
```
[INFO] Starting gunicorn
[INFO] Listening at: http://0.0.0.0:10000
[INFO] Booting worker with pid: 58
Loading faiss with AVX2 support.
Successfully loaded faiss with AVX2 support.
```

### On First Request:
- Takes 10-20 seconds (loading sentence-transformers model)
- You'll see: "RAG: Using real embeddings (all-MiniLM-L6-v2)"

### On Subsequent Requests:
- Fast response times
- Models stay loaded in memory

## Memory Usage Note

Free tier has 512MB RAM. With these optimizations:
- 1 worker instead of 2 saves ~200MB
- Lazy loading delays model loading until needed
- `--preload` shares memory across workers more efficiently

If you still experience memory issues, consider:
- Upgrading to paid tier ($7/month for 2GB RAM)
- Or switch to a lighter embedding model

## Common Post-Deployment Issues

### "Service unavailable" on first request
- This is normal - cold start + model loading
- Wait 30 seconds and refresh

### Still seeing Python 3.13
- Clear Render's build cache
- Ensure PYTHON_VERSION environment variable is set
- Check runtime.txt is committed to git

### Timeout on specific operations
- Document upload/processing may timeout on large files
- Consider implementing async processing for large uploads
- Or increase timeout further in gunicorn config

## Support

If issues persist after these fixes, check:
1. Build logs for Python version confirmation
2. Runtime logs for "RAG: Using real embeddings" message
3. Memory usage in Render metrics
4. Environment variables are set correctly
