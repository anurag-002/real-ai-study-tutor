# Authentication Setup Guide

## What Changed

Authentication has been added to the AI Study Tutor using Django's built-in auth system and Django REST Framework tokens.

### Key Features:
- ✅ User registration with username/password
- ✅ Token-based authentication for API requests
- ✅ Session authentication for Django views
- ✅ Secure login/logout
- ✅ Protected API endpoints
- ✅ Beautiful login and registration pages

### New Endpoints:
- `/api/register` - POST - Register new user
- `/api/login` - POST - Login and get token
- `/api/logout` - POST - Logout and invalidate token
- `/api/user` - GET - Get current user info
- `/admin` - Django admin interface

### Frontend Changes:
- Login page at `/login`
- Register page at `/register`
- Logout button in chat interface
- Auth token automatically included in all API requests
- Redirects to login if not authenticated

## Setup Instructions

### 1. Run Database Migrations

Since we now use Django's auth system, we need to create the database tables:

```bash
python manage.py migrate
```

This creates tables for:
- Users
- Auth tokens
- Sessions
- Groups and permissions

### 2. Create a Superuser (Optional)

To access the Django admin interface:

```bash
python manage.py createsuperuser
```

Follow the prompts to set username, email (optional), and password.

### 3. Start the Server

```bash
python manage.py runserver 0.0.0.0:8000
```

### 4. Test Authentication

1. Visit `http://localhost:8000` - Should redirect to login
2. Click "Register" to create an account
3. After registration, you'll be redirected to the chat
4. Your username will appear in the header
5. Click the logout icon to logout

## API Authentication

All API endpoints (except `/api/healthz`, `/api/login`, `/api/register`) require authentication.

### Using Token Auth (for API clients):

```bash
# Get token by logging in
curl -X POST http://localhost:8000/api/login \
  -H "Content-Type: application/json" \
  -d '{"username":"youruser","password":"yourpass"}'

# Use token in requests
curl http://localhost:8000/api/send-message \
  -H "Authorization: Token YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{"content":"Hello AI"}'
```

### Using Session Auth (for browsers):

The frontend automatically handles this by storing the token in localStorage and including it in all API requests.

## Admin Interface

Access the Django admin at `http://localhost:8000/admin` with your superuser credentials.

You can:
- Manage users
- View and edit user tokens
- Check sessions
- Manage permissions

## Security Notes

1. **CSRF Protection**: Enabled for session-based requests
2. **Token Security**: Tokens are stored in localStorage (consider using httpOnly cookies for production)
3. **Password Validation**: Django's built-in validators enforce:
   - Minimum 6 characters
   - Not too similar to username
   - Not commonly used passwords
   - Not entirely numeric

## Production Checklist

For production deployment:

- [ ] Set `DEBUG = False` in settings.py
- [ ] Change `SECRET_KEY` to a secure random value
- [ ] Use HTTPS for all requests
- [ ] Set proper `ALLOWED_HOSTS`
- [ ] Use environment variables for secrets
- [ ] Consider using httpOnly cookies instead of localStorage
- [ ] Enable rate limiting
- [ ] Set up proper CORS policies
- [ ] Use a production database (PostgreSQL)
- [ ] Set up proper session backend (Redis/Memcached)

## Troubleshooting

**"No such table: auth_user"**
- Run `python manage.py migrate`

**"Invalid token"**
- Token may have been deleted or expired
- Logout and login again

**"Authentication credentials were not provided"**
- Token not included in request headers
- Check that `Authorization: Token YOUR_TOKEN` header is set

**Can't login after registration**
- Check console for errors
- Verify token is being stored in localStorage
- Clear browser cache and try again

## Database

The app now uses two databases:
1. **`db.sqlite3`** - Django's database (users, tokens, sessions)
2. **`data/sessions.sqlite3`** - Custom database (chat history)

This keeps Django's system separate from the app's data.
