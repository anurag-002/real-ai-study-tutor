# Session Isolation Fix + Scoreboard Feature

## Problem Fixed
Sessions were showing for all users because the `sessions` table didn't track which user owned each session.

## Changes Made

### 1. Database Schema Updates (`backend/db.py`)
- Added `user_id` column to `sessions` table
- Created `user_stats` table to track:
  - Total messages, files uploaded, study time
  - Points system (1 point per message, 5 per file)
  - Current streak and longest streak
- Created `daily_activity` table for streak tracking
- Added migration code to update existing databases

### 2. Session Management
- `ensure_session()` now accepts `user_id` parameter
- `get_all_sessions()` filters by `user_id` when provided
- All session creation/access now links to authenticated user

### 3. Views Updated (`backend/views.py`)
- `send_message()` - Links session to user on creation
- `list_sessions()` - Only shows user's own sessions
- `get_session_history()` - Associates session with user
- `create_new_session()` - Links new session to user
- `upload_file()` - Tracks file uploads in user stats

### 4. New Scoreboard API Endpoints
- `GET /api/scoreboard?limit=10` - Get top users leaderboard
- `GET /api/user-stats?session_id=X` - Get user's stats and rank
- `POST /api/update-stats` - Manually update stats

### 5. Points System
- 1 point per message sent
- 5 points per file uploaded
- 1 point per 5 minutes of study time
- Streak bonuses for consecutive daily activity

## How It Works Now

### Session Isolation
1. When user logs in and sends a message, `user_id` is attached to session
2. `list_sessions()` filters to only show that user's sessions
3. Each user sees only their own chat history

### Scoreboard Features
- Automatically tracks messages when users chat
- Tracks file uploads when documents are uploaded
- Calculates daily streaks based on activity
- Ranks users by total points
- Shows individual user rank and stats

## API Usage Examples

```javascript
// Get leaderboard
fetch('/api/scoreboard?limit=10')

// Get user stats
fetch('/api/user-stats?session_id=your-session-id')

// Manually track study time (5 minutes)
fetch('/api/update-stats', {
  method: 'POST',
  body: JSON.stringify({
    session_id: 'session-id',
    activity_type: 'study_time',
    value: 5
  })
})
```

## What's Next
- Frontend UI for displaying scoreboard
- Achievements/badges system
- Weekly/monthly leaderboards
- Study goals and reminders
