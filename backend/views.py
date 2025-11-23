import os
import uuid
import time
from datetime import datetime, timezone
from typing import Optional

from django.http import JsonResponse, HttpResponse, FileResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.shortcuts import redirect, render
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authtoken.models import Token

from .db import (init_db, append_message, get_history, reset_history_if_exists, ensure_session, 
                get_all_sessions, delete_session, get_or_create_user_stats, update_user_activity,
                get_leaderboard, get_user_rank)
from .rag import get_or_create_index, search_similar_snippets, upsert_documents, clear_index
from .groq_client import generate_text_with_context, transcribe_audio, extract_text_from_image
from .tts import synthesize_tts
from .utils import save_upload_temporarily, read_text_file
from pathlib import Path

# Initialize paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = DATA_DIR / "uploads"
AUDIO_DIR = DATA_DIR / "audio"
INDEX_DIR = DATA_DIR / "index"

# Initialize database
init_db(str(DATA_DIR / "sessions.sqlite3"))


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ============ Authentication Views ============

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def register_user(request):
    """Register a new user"""
    try:
        data = request.data
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '')
        
        # Validation
        if not username or not password:
            return Response(
                {'error': 'Username and password are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if len(password) < 6:
            return Response(
                {'error': 'Password must be at least 6 characters'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if User.objects.filter(username=username).exists():
            return Response(
                {'error': 'Username already exists'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )
        
        # Create auth token
        token, _ = Token.objects.get_or_create(user=user)
        
        print(f"AUTH: New user registered - {username}")
        
        return Response({
            'success': True,
            'message': 'User registered successfully',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
            },
            'token': token.key,
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        print(f"AUTH: Registration failed: {e}")
        import traceback
        traceback.print_exc()
        error_msg = str(e) if DEBUG else 'Registration failed. Please try again.'
        return Response(
            {'error': error_msg, 'debug': str(e) if DEBUG else None},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def login_user(request):
    """Login user and return token"""
    try:
        data = request.data
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        if not username or not password:
            return Response(
                {'error': 'Username and password are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Authenticate
        user = authenticate(username=username, password=password)
        
        if user is None:
            return Response(
                {'error': 'Invalid username or password'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Login user (for session-based auth)
        login(request, user)
        
        # Get or create token
        token, _ = Token.objects.get_or_create(user=user)
        
        print(f"AUTH: User logged in - {username}")
        
        return Response({
            'success': True,
            'message': 'Login successful',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
            },
            'token': token.key,
        })
        
    except Exception as e:
        print(f"AUTH: Login failed: {e}")
        import traceback
        traceback.print_exc()
        return Response(
            {'error': 'Login failed. Please try again.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_user(request):
    """Logout user and delete token"""
    try:
        # Delete user's token
        if hasattr(request.user, 'auth_token'):
            request.user.auth_token.delete()
        
        # Logout from session
        logout(request)
        
        print(f"AUTH: User logged out - {request.user.username}")
        
        return Response({
            'success': True,
            'message': 'Logout successful'
        })
        
    except Exception as e:
        print(f"AUTH: Logout failed: {e}")
        return Response(
            {'error': 'Logout failed'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_info(request):
    """Get current user information"""
    return Response({
        'user': {
            'id': request.user.id,
            'username': request.user.username,
            'email': request.user.email,
        }
    })


# ============ Frontend Pages ============

def login_page(request):
    """Serve login page"""
    return render(request, 'login.html')


def register_page(request):
    """Serve registration page"""
    return render(request, 'register.html')


# ============ API Views (Protected) ============


@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_message(request):
    """Handle text/voice message from user"""
    try:
        data = request.data
        session_id = data.get('session_id') or str(uuid.uuid4())
        user_text = data.get('content', '').strip()
        
        if not user_text:
            return Response(
                {'error': 'Message content is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get user_id from authenticated user
        user_id = str(request.user.id) if request.user.is_authenticated else None
        ensure_session(session_id, user_id)
        print(f"MAIN: Processing message: '{user_text[:50]}...'")
        
        # Generate AI response
        try:
            use_reasoning = request.META.get('HTTP_X_REASONING', '').lower() in ('true', '1', 'yes')
            reply_text = generate_text_with_context(user_text, use_reasoning=use_reasoning)
            print(f"MAIN: Generated reply: '{reply_text[:50]}...'")
        except Exception as e:
            print(f"MAIN: Text generation failed: {e}")
            import traceback
            traceback.print_exc()
            reply_text = "I apologize, but I encountered an error generating a response. Please try again."
        
        # Save to history
        ts = now_iso()
        append_message(session_id, sender="user", content=user_text, audio_url=None, timestamp=ts)
        append_message(session_id, sender="ai", content=reply_text, audio_url=None, timestamp=ts)
        
        return Response({
            'session_id': session_id,
            'reply_text': reply_text,
            'reply_audio_url': None,
            'timestamp': ts,
        })
    except Exception as e:
        print(f"MAIN: Critical error in send_message: {e}")
        import traceback
        traceback.print_exc()
        return Response(
            {'error': 'An unexpected error occurred. Please try again.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_tts(request):
    """Generate TTS for a specific message on demand"""
    data = request.data
    message_id = data.get('message_id')
    voice = request.META.get('HTTP_X_VOICE') or 'Gail-PlayAI'
    
    if not message_id:
        return Response({'error': 'message_id required'}, status=status.HTTP_400_BAD_REQUEST)
    
    text = data.get('text')
    if not text:
        return Response({'error': 'text required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        audio_filename = f"tts_{int(time.time())}.wav"
        audio_path = AUDIO_DIR / audio_filename
        print(f"MAIN: Generating TTS for '{text[:30]}...' with voice {voice}")
        synthesize_tts(text, str(audio_path), voice=voice)
        audio_rel_url = f"/audio/{audio_filename}"
        print(f"MAIN: TTS completed, audio URL: {audio_rel_url}")
        
        return Response({
            'success': True,
            'audio_url': audio_rel_url
        })
    except Exception as e:
        print(f"MAIN: TTS failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@csrf_exempt
@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser])
@permission_classes([IsAuthenticated])
def upload_file(request):
    """Handle file uploads (documents, images, audio)"""
    try:
        session_id = request.POST.get('session_id') or str(uuid.uuid4())
        user_note = request.POST.get('user_note')
        file = request.FILES.get('file')
        
        if not file:
            return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate file size (max 50MB)
        if file.size > 50 * 1024 * 1024:
            return Response(
                {'error': 'File too large. Maximum size is 50MB.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        ensure_session(session_id)
        print(f"UPLOAD: Processing file '{file.name}' ({file.size} bytes)")
        
        # Save upload to disk
        try:
            temp_path = save_upload_temporarily(file, str(UPLOADS_DIR))
        except Exception as e:
            print(f"UPLOAD: Failed to save file: {e}")
            return Response(
                {'error': 'Failed to save uploaded file'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Determine handling based on content type / extension
        filename_lower = file.name.lower() if file.name else ""
        text_content: Optional[str] = None
        
        try:
            if filename_lower.endswith((".pdf", ".docx", ".txt")):
                text_content = read_text_file(temp_path)
                if not text_content:
                    return Response(
                        {'error': 'Could not extract text from document. Please check the file format.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            elif filename_lower.endswith((".png", ".jpg", ".jpeg")):
                try:
                    text_content = extract_text_from_image(temp_path)
                except Exception as e:
                    print(f"UPLOAD: Image OCR failed: {e}")
                    text_content = None
            elif filename_lower.endswith((".webm", ".wav", ".mp3", ".m4a", ".ogg")):
                try:
                    text_content = transcribe_audio(temp_path)
                except Exception as e:
                    print(f"UPLOAD: Audio transcription failed: {e}")
                    text_content = None
            else:
                return Response(
                    {'error': 'Unsupported file format. Please upload PDF, DOCX, TXT, images, or audio files.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            is_audio = filename_lower.endswith((".webm", ".wav", ".mp3", ".m4a", ".ogg"))
            is_doc = filename_lower.endswith((".pdf", ".docx", ".txt"))
            
            # For transcribed audio: treat transcription as a user message
            if is_audio and text_content and text_content.strip():
                user_text = text_content.strip()
                query_text = f"{user_note.strip()}\n\n{user_text}" if user_note else user_text
                index = get_or_create_index(str(INDEX_DIR))
                retrieved = search_similar_snippets(index=index, query_text=query_text, k=3)
                try:
                    use_reasoning = request.META.get('HTTP_X_REASONING', '').lower() == 'true'
                    reply_text = generate_text_with_context(query=query_text, retrieved_snippets=retrieved, use_reasoning=use_reasoning)
                except Exception as e:
                    print(f"UPLOAD: AI response failed: {e}")
                    reply_text = "I transcribed your audio but encountered an error generating a response."
                ts = now_iso()
                if user_note and user_note.strip():
                    append_message(session_id, sender="user", content=user_note.strip(), audio_url=None, timestamp=ts)
                append_message(session_id, sender="user", content=user_text, audio_url=None, timestamp=ts)
            else:
                # Ingest documents/images with extracted text
                if is_doc and text_content and text_content.strip():
                    try:
                        index = get_or_create_index(str(INDEX_DIR))
                        upsert_documents(index=index, docs=[{"session_id": session_id, "text": text_content, "source": filename_lower or "upload"}])
                    except Exception as e:
                        print(f"UPLOAD: Failed to index document: {e}")
                
                # Prepare helpful AI confirmation response
                base_prompt = f"A new study document '{file.name}' was uploaded. Provide a helpful brief summary and suggest how to study it."
                user_prompt = f"{user_note.strip()}\n\n{base_prompt}" if user_note else base_prompt
                retrieved = []
                if text_content:
                    retrieved = [text_content[:1200]]
                try:
                    use_reasoning = request.META.get('HTTP_X_REASONING', '').lower() == 'true'
                    reply_text = generate_text_with_context(query=user_prompt, retrieved_snippets=retrieved, use_reasoning=use_reasoning)
                except Exception as e:
                    print(f"UPLOAD: AI response failed: {e}")
                    reply_text = f"Successfully uploaded {file.name}. The document has been added to your knowledge base."
                ts = now_iso()
                label = "audio" if is_audio else "file"
                if user_note and user_note.strip():
                    append_message(session_id, sender="user", content=user_note.strip(), audio_url=None, timestamp=ts)
                append_message(session_id, sender="user", content=f"[Uploaded {label}] {file.name}", audio_url=None, timestamp=ts)
            
            append_message(session_id, sender="ai", content=reply_text, audio_url=None, timestamp=ts)
            
            # Track file upload in stats
            update_user_activity(session_id, 'file', 1)
            
            return Response({
                'session_id': session_id,
                'reply_text': reply_text,
                'reply_audio_url': None,
                'timestamp': ts,
            })
        except Exception as e:
            print(f"UPLOAD: Processing error: {e}")
            import traceback
            traceback.print_exc()
            return Response(
                {'error': 'Failed to process file. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    except Exception as e:
        print(f"UPLOAD: Critical error: {e}")
        import traceback
        traceback.print_exc()
        return Response(
            {'error': 'An unexpected error occurred during upload.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_session_history(request):
    """Get conversation history for a session"""
    session_id = request.GET.get('session_id')
    if not session_id:
        return Response({'error': 'session_id is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Get user_id from authenticated user
    user_id = str(request.user.id) if request.user.is_authenticated else None
    ensure_session(session_id, user_id)
    messages = get_history(session_id)
    return Response({
        'session_id': session_id,
        'messages': messages
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_sessions(request):
    """List all chat sessions for the authenticated user"""
    user_id = str(request.user.id) if request.user.is_authenticated else None
    sessions = get_all_sessions(user_id)
    return Response({
        'sessions': sessions
    })


@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reset_history(request):
    """Reset conversation history for a session"""
    data = request.data
    session_id = data.get('session_id')
    if not session_id:
        return Response({'error': 'session_id is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    reset_history_if_exists(session_id)
    return Response({'success': True})


@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def delete_session_view(request):
    """Delete a session and all its messages"""
    data = request.data
    session_id = data.get('session_id')
    if not session_id:
        return Response({'error': 'session_id is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    delete_session(session_id)
    return Response({'success': True})


@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_new_session(request):
    """Create a new chat session"""
    new_session_id = str(uuid.uuid4())
    user_id = str(request.user.id) if request.user.is_authenticated else None
    ensure_session(new_session_id, user_id)
    return Response({
        'session_id': new_session_id,
        'created_at': now_iso()
    })


@csrf_exempt
@api_view(['POST'])
def reset_index():
    """Clear the RAG index"""
    clear_index(str(INDEX_DIR))
    return Response({'success': True})


@csrf_exempt
@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser])
def transcribe(request):
    """Transcribe audio only and return text without creating messages"""
    file = request.FILES.get('file')
    if not file:
        return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)
    
    temp_path = save_upload_temporarily(file, str(UPLOADS_DIR))
    try:
        text = transcribe_audio(temp_path) or ""
        return Response({'text': text})
    finally:
        pass


@api_view(['GET'])
@permission_classes([AllowAny])
def healthz(request):
    """Health check endpoint"""
    return Response({'ok': True})


def root_redirect(request):
    """Redirect root to static frontend"""
    return redirect('/static/index.html')


def favicon(request):
    """Return empty response for favicon"""
    return HttpResponse(status=204)


# Scoreboard endpoints
@api_view(['GET'])
@permission_classes([AllowAny])
def get_scoreboard(request):
    """Get leaderboard data"""
    limit = int(request.GET.get('limit', 10))
    leaderboard = get_leaderboard(limit)
    return Response({'leaderboard': leaderboard})


@api_view(['GET'])
@permission_classes([AllowAny])
def get_user_stats(request):
    """Get current user's stats and rank"""
    session_id = request.GET.get('session_id', 'default')
    stats = get_user_rank(session_id)
    return Response({'stats': stats})


@api_view(['POST'])
@permission_classes([AllowAny])
def update_stats(request):
    """Manually update user stats (for file uploads, etc)"""
    data = request.data
    session_id = data.get('session_id', 'default')
    activity_type = data.get('activity_type', 'message')  # 'message', 'file', or 'study_time'
    value = data.get('value', 1)
    
    update_user_activity(session_id, activity_type, value)
    stats = get_user_rank(session_id)
    
    return Response({'success': True, 'stats': stats})
