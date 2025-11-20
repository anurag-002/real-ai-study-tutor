let sessionId = null;
const apiBase = "";

// Check authentication on load
function checkAuth() {
  const token = localStorage.getItem('authToken');
  if (!token) {
    window.location.href = '/login';
    return false;
  }
  return true;
}

// Get CSRF token from cookie
function getCsrfToken() {
  const name = 'csrftoken';
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

// Get auth headers
function getAuthHeaders() {
  const token = localStorage.getItem('authToken');
  const headers = {
    'Authorization': `Token ${token}`
  };
  
  // Add CSRF token for POST requests
  const csrfToken = getCsrfToken();
  if (csrfToken) {
    headers['X-CSRFToken'] = csrfToken;
  }
  
  return headers;
}

// Check auth and show username
window.addEventListener('load', () => {
  if (!checkAuth()) return;
  
  const username = localStorage.getItem('username');
  if (username) {
    const usernameEl = document.getElementById('current-username');
    if (usernameEl) {
      usernameEl.textContent = `(@${username})`;
    }
  }
  
  // Load saved session from localStorage or start new
  const savedSessionId = localStorage.getItem('currentSessionId');
  if (savedSessionId) {
    sessionId = savedSessionId;
    loadHistory();
  }
  
  // Load sessions list
  loadSessionsList();
});

// Load all chat sessions for sidebar
async function loadSessionsList() {
  try {
    const res = await fetch(`${apiBase}/api/sessions`, {
      headers: getAuthHeaders()
    });
    const data = await res.json();
    
    const sessionsEl = document.getElementById('sessions');
    if (!sessionsEl) return;
    
    sessionsEl.innerHTML = '';
    
    if (data.sessions && data.sessions.length > 0) {
      data.sessions.forEach(session => {
        const li = document.createElement('li');
        li.className = 'session-item';
        
        // Create preview text from first message
        let preview = session.first_message || 'New chat';
        if (preview.length > 40) {
          preview = preview.substring(0, 40) + '...';
        }
        
        const isActive = session.session_id === sessionId;
        
        li.innerHTML = `
          <div class="session-preview ${isActive ? 'active' : ''}" data-session-id="${session.session_id}">
            <div class="session-text">${escapeHtml(preview)}</div>
            <div class="session-time">${formatDate(session.created_at)}</div>
            <button class="delete-session-btn" title="Delete chat">
              <i class="fa-solid fa-trash"></i>
            </button>
          </div>
        `;
        
        // Click to load this session
        li.querySelector('.session-preview').addEventListener('click', (e) => {
          if (!e.target.closest('.delete-session-btn')) {
            loadSession(session.session_id);
          }
        });
        
        // Delete button
        li.querySelector('.delete-session-btn').addEventListener('click', async (e) => {
          e.stopPropagation();
          if (confirm('Delete this chat? This cannot be undone.')) {
            await deleteSession(session.session_id);
          }
        });
        
        sessionsEl.appendChild(li);
      });
    } else {
      sessionsEl.innerHTML = '<li class="text-gray-400 pl-7">No previous chats</li>';
    }
  } catch (err) {
    console.error('Failed to load sessions:', err);
  }
}

// Load a specific session
async function loadSession(sid) {
  sessionId = sid;
  localStorage.setItem('currentSessionId', sid);
  messagesEl.innerHTML = '';
  await loadHistory();
  await loadSessionsList(); // Refresh to show active state
}

// Start a new chat
async function startNewChat() {
  try {
    const res = await fetch(`${apiBase}/api/new-session`, {
      method: 'POST',
      headers: {
        ...getAuthHeaders(),
        'Content-Type': 'application/json'
      }
    });
    const data = await res.json();
    
    sessionId = data.session_id;
    localStorage.setItem('currentSessionId', sessionId);
    messagesEl.innerHTML = '';
    await loadSessionsList();
  } catch (err) {
    console.error('Failed to create new session:', err);
  }
}

// Delete a session
async function deleteSession(sid) {
  try {
    const res = await fetch(`${apiBase}/api/delete-session`, {
      method: 'POST',
      headers: {
        ...getAuthHeaders(),
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ session_id: sid })
    });
    
    if (res.ok) {
      // If we deleted the current session, start a new one
      if (sid === sessionId) {
        await startNewChat();
      } else {
        await loadSessionsList();
      }
    }
  } catch (err) {
    console.error('Failed to delete session:', err);
  }
}

// Helper to escape HTML
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// Helper to format date
function formatDate(isoStr) {
  if (!isoStr) return '';
  try {
    const date = new Date(isoStr);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);
    
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  } catch {
    return '';
  }
}

// Setup new chat button
document.addEventListener('DOMContentLoaded', () => {
  const newChatBtn = document.getElementById('new-chat-btn');
  if (newChatBtn) {
    newChatBtn.addEventListener('click', startNewChat);
  }
});

// Logout function
function handleLogout() {
  const token = localStorage.getItem('authToken');
  if (token) {
    fetch(`${apiBase}/api/logout`, {
      method: 'POST',
      headers: getAuthHeaders()
    }).finally(() => {
      localStorage.removeItem('authToken');
      localStorage.removeItem('username');
      localStorage.removeItem('currentSessionId');
      window.location.href = '/login';
    });
  }
}

const messagesEl = document.getElementById("messages");
const sessionsEl = document.getElementById("sessions");
const inputEl = document.getElementById("text-input");
const sendBtn = document.getElementById("send-btn");
const voiceBtn = document.getElementById("voice-btn");
const fileInput = document.getElementById("file-input");
const uploadBtn = document.getElementById("upload-btn");
const recIndicator = document.getElementById("rec-indicator");
const settingsBtn = document.getElementById("settings-btn");
const settingsModal = document.getElementById("settings-modal");
const voiceSelect = document.getElementById("voice-select");
const settingsSave = document.getElementById("settings-save");
const settingsCancel = document.getElementById("settings-cancel");
const stagedFileEl = document.getElementById("staged-file");
let stagedFile = null;

// Simulate loading for 2 seconds
window.addEventListener('load', () => {
    setTimeout(() => {
        document.getElementById('loader').style.display = 'none';
        document.getElementById('content').style.display = 'block';
    }, 2000);
});



function initTiltCards() {
  const tiltContainers = document.querySelectorAll(".tilt-container");

  tiltContainers.forEach((container) => {
    const card = container.querySelector(".tilt-card");
    const rotateAmplitude = 12;
    const scaleOnHover = 1.05;

    let targetX = 0, targetY = 0;
    let currentX = 0, currentY = 0;
    let animationFrame;

    function animate() {
      // Lerp (ease) toward target
      currentX += (targetX - currentX) * 0.1;
      currentY += (targetY - currentY) * 0.1;

      card.style.transform = `rotateX(${currentX}deg) rotateY(${currentY}deg) scale(${scaleOnHover})`;

      animationFrame = requestAnimationFrame(animate);
    }

    container.addEventListener("mousemove", (e) => {
      const rect = container.getBoundingClientRect();
      const offsetX = e.clientX - rect.left - rect.width / 2;
      const offsetY = e.clientY - rect.top - rect.height / 2;

      targetX = (-offsetY / (rect.height / 2)) * rotateAmplitude;
      targetY = (offsetX / (rect.width / 2)) * rotateAmplitude;

      if (!animationFrame) animate();
    });

    container.addEventListener("mouseenter", () => {
      card.style.transition = "transform 0.1s ease-out";
      animationFrame = requestAnimationFrame(animate);
    });

    container.addEventListener("mouseleave", () => {
      cancelAnimationFrame(animationFrame);
      animationFrame = null;
      card.style.transition = "transform 0.3s ease";
      card.style.transform = "rotateX(0deg) rotateY(0deg) scale(1)";
      targetX = 0;
      targetY = 0;
      currentX = 0;
      currentY = 0;
    });
  });
}

document.addEventListener("DOMContentLoaded", initTiltCards);

document.addEventListener("DOMContentLoaded", () => {
  if (!document.querySelector(".cursor")) {
    const cursorEl = document.createElement("div");
    cursorEl.className =
      "cursor fixed top-0 left-0 w-[30px] h-[30px] border-2 border-white rounded-full pointer-events-none -translate-x-1/2 -translate-y-1/2 scale-100 transition-transform ease-in-out duration-150 z-[9999] shadow-[0_0_8px_rgba(255,255,255,0.6)]";
    document.body.appendChild(cursorEl);
  }
});


// Configure marked when it's available
function configureMarked() {
  if (window.marked) {
    marked.setOptions({
      gfm: true,
      breaks: true,
      headerIds: false,
      mangle: false,
    });
    console.log("Marked configured with GFM breaks");
    return true;
  }
  return false;
}

function addMessage(sender, content, audioUrl) {
  const el = document.createElement("div");
  el.className = `message ${sender}`;

  // Ensure marked is configured
  configureMarked();

  // Render markdown if available, sanitize, else escape
  let html = content;
  try {
    if (window.marked) {
      console.log("Parsing markdown:", content.substring(0, 100) + "...");
      html = window.marked.parse(content);
      console.log("Parsed HTML:", html.substring(0, 100) + "...");
    } else {
      console.warn("Marked library not available");
    }
  } catch (err) {
    console.error("Markdown parsing error:", err);
  }

  try {
    if (window.DOMPurify) {
      html = window.DOMPurify.sanitize(html);
    } else {
      html = html.replace(/</g, "&lt;");
    }
  } catch (err) {
    console.error("HTML sanitization error:", err);
    html = html.replace(/</g, "&lt;");
  }

  el.innerHTML = `<div>${html}</div>`;

  // Add speaker button for AI messages (no audioUrl by default)
  if (sender === "ai") {
    const btn = document.createElement("button");
    btn.textContent = "🔊";
    btn.className = "audio-btn";
    btn.onclick = async () => {
      // Generate TTS on demand
      if (!btn._audioInstance) {
        try {
          btn.textContent = "⏳";
          btn.disabled = true;

          const selVoice = localStorage.getItem("voice") || "Gail-PlayAI";
          const response = await fetch(`${apiBase}/generate-tts`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "X-Voice": selVoice,
            },
            body: JSON.stringify({
              text: content,
            }),
          });

          const data = await response.json();
          if (data.success && data.audio_url) {
            const audio = new Audio(data.audio_url);
            btn._audioInstance = audio;
            btn.textContent = "🔊";
            btn.disabled = false;
          } else {
            console.error("TTS generation failed:", data.error);
            btn.textContent = "❌";
            btn.disabled = false;
          }
        } catch (err) {
          console.error("TTS request failed:", err);
          btn.textContent = "❌";
          btn.disabled = false;
        }
      }

      // Play audio
      if (btn._audioInstance) {
        let audio = btn._audioInstance;
        if (!btn._playing) {
          btn._playing = true;
          btn.textContent = "⏹️";
          audio.onended = () => {
            btn._playing = false;
            btn.textContent = "🔊";
          };
          audio.onerror = (e) => {
            btn._playing = false;
            btn.textContent = "🔊";
            console.error("Audio playback error:", e);
          };
          audio.play().catch((e) => {
            btn._playing = false;
            btn.textContent = "🔊";
            console.error("Audio play failed:", e);
          });
        } else {
          try {
            audio.pause();
            audio.currentTime = 0;
          } catch {}
          btn._playing = false;
          btn.textContent = "🔊";
        }
      }
    };
    el.appendChild(btn);
  }

  messagesEl.appendChild(el);
  messagesEl.scrollTop = messagesEl.scrollHeight;

  // Trigger MathJax typesetting for this message if available
  try {
    if (window.MathJax && window.MathJax.typesetPromise) {
      window.MathJax.typesetPromise([el]).catch(() => {});
    }
  } catch {}
}

async function sendText() {
  const text = inputEl.value.trim();
  if (!text && !stagedFile) return;
  if (text) addMessage("user", text);
  inputEl.value = "";
  const selVoice = localStorage.getItem("voice");

  if (stagedFile) {
    const form = new FormData();
    if (sessionId) form.append("session_id", sessionId);
    form.append("file", stagedFile);
    form.append("user_note", text || "");
    const headers = getAuthHeaders();
    if (selVoice) headers["X-Voice"] = selVoice;
    headers["X-Reasoning"] = "true";
    const res = await fetch(`${apiBase}/api/upload-file`, {
      method: "POST",
      headers,
      body: form,
    });
    const data = await res.json();
    sessionId = data.session_id;
    addMessage("ai", data.reply_text, data.reply_audio_url);
    stagedFile = null;
    if (stagedFileEl) {
      stagedFileEl.style.display = "none";
      stagedFileEl.textContent = "";
    }
    loadHistory();
    loadSessionsList(); // Refresh sessions sidebar
    return;
  }

  const headers = { "Content-Type": "application/json", ...getAuthHeaders() };
  if (selVoice) headers["X-Voice"] = selVoice;
  headers["X-Reasoning"] = "true";
  const res = await fetch(`${apiBase}/api/send-message`, {
    method: "POST",
    headers,
    body: JSON.stringify({
      session_id: sessionId,
      input_type: "text",
      content: text,
    }),
  });
  const data = await res.json();
  sessionId = data.session_id;
  addMessage("ai", data.reply_text, data.reply_audio_url);
  loadHistory();
  loadSessionsList(); // Refresh sessions sidebar
}

async function loadHistory() {
  if (!sessionId) return;
  const res = await fetch(
    `${apiBase}/api/history?session_id=${encodeURIComponent(sessionId)}`,
    {
      headers: getAuthHeaders()
    }
  );
  const data = await res.json();
  messagesEl.innerHTML = "";
  for (const m of data.messages) {
    addMessage(m.sender, m.content, m.audio_url);
  }
}

async function uploadSelectedFile(file) {
  // If audio file, transcribe and place text into input for editing first
  if (file && file.type && file.type.startsWith("audio/")) {
    const tform = new FormData();
    tform.append("file", file);
    const tres = await fetch(`${apiBase}/transcribe`, {
      method: "POST",
      body: tform,
    });
    const tdata = await tres.json();
    if (tdata && typeof tdata.text === "string") {
      inputEl.value = tdata.text;
      try {
        inputEl.focus();
      } catch {}
    } else {
      alert("Could not transcribe audio.");
    }
    return;
  }

  const form = new FormData();
  if (sessionId) form.append("session_id", sessionId);
  form.append("file", file);
  const voiceHeaders = {};
  const selVoice2 = localStorage.getItem("voice");
  if (selVoice2) voiceHeaders["X-Voice"] = selVoice2;
  const res = await fetch(`${apiBase}/upload-file`, {
    method: "POST",
    headers: voiceHeaders,
    body: form,
  });
  const data = await res.json();
  sessionId = data.session_id;
  addMessage("ai", data.reply_text, data.reply_audio_url);
  loadHistory();
}

sendBtn.onclick = sendText;
inputEl.addEventListener("keydown", (e) => {
  if (e.key === "Enter") sendText();
});

fileInput.onchange = () => {
  if (fileInput.files && fileInput.files[0]) {
    stagedFile = fileInput.files[0];
    if (stagedFileEl) {
      stagedFileEl.style.display = "inline";
      stagedFileEl.textContent = `Ready: ${stagedFile.name}`;
    }
    fileInput.value = "";
  }
};

uploadBtn.onclick = () => {
  fileInput.click();
};

// Settings modal logic
function loadSettings() {
  const v = localStorage.getItem("voice") || "Gail-PlayAI";
  if (voiceSelect) voiceSelect.value = v;
  const r = localStorage.getItem("reasoning") === "true";
  const reasoningToggle = document.getElementById("reasoning-toggle");
  if (reasoningToggle) reasoningToggle.checked = r;
}
function saveSettings() {
  const v = voiceSelect ? voiceSelect.value : "Gail-PlayAI";
  localStorage.setItem("voice", v);
  const reasoningToggle = document.getElementById("reasoning-toggle");
  const r = reasoningToggle ? reasoningToggle.checked : false;
  localStorage.setItem("reasoning", r ? "true" : "false");
}
function openSettings() {
  loadSettings();
  if (settingsModal) settingsModal.style.display = "flex";
}
function closeSettings() {
  if (settingsModal) settingsModal.style.display = "none";
}
if (settingsBtn) settingsBtn.onclick = openSettings;
if (settingsCancel) settingsCancel.onclick = closeSettings;
if (settingsSave)
  settingsSave.onclick = () => {
    saveSettings();
    closeSettings();
  };

// Basic MediaRecorder voice capture, sends as file to /upload-file
let mediaRecorder = null;
let chunks = [];
let recording = false;

async function getSupportedMimeType() {
  const candidates = [
    "audio/webm;codecs=opus",
    "audio/webm",
    "audio/ogg;codecs=opus",
    "audio/ogg",
  ];
  for (const type of candidates) {
    if (MediaRecorder.isTypeSupported && MediaRecorder.isTypeSupported(type))
      return type;
  }
  return "";
}

async function initRecorder() {
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    alert("Microphone not supported in this browser. Try Chrome or Edge.");
    console.warn("getUserMedia not supported");
    return null;
  }
  try {
    console.log("Requesting microphone...");
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const mimeType = await getSupportedMimeType();
    const options = mimeType ? { mimeType } : undefined;
    console.log("MediaRecorder options:", options);
    const rec = new MediaRecorder(stream, options);
    rec.ondataavailable = (e) => {
      if (e.data && e.data.size > 0) chunks.push(e.data);
    };
    rec.onstop = async () => {
      try {
        const blobType = mimeType || "audio/webm";
        const ext = blobType.includes("ogg") ? "ogg" : "webm";
        const blob = new Blob(chunks, { type: blobType });
        chunks = [];
        const file = new File([blob], `voice.${ext}`, { type: blobType });
        // Transcribe first, then place into input box
        const form = new FormData();
        form.append("file", file);
        const res = await fetch(`${apiBase}/transcribe`, {
          method: "POST",
          body: form,
        });
        const data = await res.json();
        if (data && typeof data.text === "string") {
          inputEl.value = data.text;
        } else {
          alert("Could not transcribe audio.");
        }
      } catch (err) {
        console.error("Upload failed", err);
        alert("Failed to upload recording.");
      }
      // Stop all tracks
      try {
        rec.stream.getTracks().forEach((t) => t.stop());
      } catch {}
      // Allow re-initialization next time
      mediaRecorder = null;
    };
    return rec;
  } catch (err) {
    console.error("Mic permission error", err);
    alert("Microphone access denied or unavailable.");
    return null;
  }
}

voiceBtn.onclick = async () => {
  if (!mediaRecorder) {
    mediaRecorder = await initRecorder();
    if (!mediaRecorder) return;
  }
  if (recording) {
    try {
      mediaRecorder.stop();
    } catch {}
    recording = false;
    voiceBtn.textContent = "🎤";
    voiceBtn.disabled = false;
    if (recIndicator) recIndicator.style.display = "none";
  } else {
    chunks = [];
    try {
      mediaRecorder.start();
      recording = true;
      voiceBtn.textContent = "⏹️";
      voiceBtn.disabled = false;
      if (recIndicator) recIndicator.style.display = "inline";
    } catch (err) {
      console.error("Failed to start recording", err);
      alert("Failed to start recording.");
    }
  }
};
