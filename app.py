
 # ====================================================================
# CHAT ROUTE
# ====================================================================

@app.route('/api/chat', methods=['POST'])
@login_required
@limiter.limit("30 per minute")
def chat():
    data = request.json
    message = data.get('message', '').strip()
    session_id = data.get('session_id')
    stream = data.get('stream', False)
    
    if not message:
        return jsonify({'error': 'Message is required'}), 400
    
    user = get_user()
    
    # Get or create session
    if session_id:
        chat_session = ChatSession.query.filter_by(id=session_id, user_id=user.id).first()
        if not chat_session:
            return jsonify({'error': 'Session not found'}), 404
    else:
        chat_session = ChatSession(user_id=user.id)
        db.session.add(chat_session)
        db.session.commit()
    
    # Save user message
    user_msg = ChatMessage(
        session_id=chat_session.id,
        role='user',
        content=message
    )
    db.session.add(user_msg)
    db.session.commit()
    
    # Update session title (first message)
    if chat_session.messages.count() == 1:
        chat_session.title = message[:50] + ('...' if len(message) > 50 else '')
        db.session.commit()
    
    # Get conversation context
    context_messages = AIEngine.get_conversation_context(chat_session.id, limit=20)
    language = detect_language(message)
    
    # Prepare messages for AI
    ai_messages = [
        {"role": "system", "content": f"""You are Dark Wave AI, a helpful, intelligent, and friendly assistant.
        Current language: {language}
        Guidelines:
        - Be concise but informative
        - Use markdown for formatting when helpful
        - Be empathetic and engaging
        - Provide accurate information
        - If unsure, say so honestly
        """}
    ] + context_messages
    
    try:
        # Get AI response
        if openai_client:
            response = openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=ai_messages,
                max_tokens=500,
                temperature=0.7
            )
            ai_reply = response.choices[0].message.content
        else:
            ai_reply = f"""✨ *Dark Wave AI (Demo Mode)* ✨

You said: "{message}"

To enable full AI features:
1. Get an API key from [OpenAI](https://platform.openai.com)
2. Add it to the `.env` file
3. Restart the application

**Available Features:**
- 💬 Chat history
- 🔒 User authentication  
- 📱 Responsive design
- 🌍 Multi-language support
- 🎨 Modern UI

*Upgrade to unlock full AI capabilities!*"""
        
        # Save AI response
        ai_msg = ChatMessage(
            session_id=chat_session.id,
            role='assistant',
            content=ai_reply,
            tokens=len(ai_reply.split())
        )
        db.session.add(ai_msg)
        db.session.commit()
        
        # Format response with markdown
        formatted_reply = format_markdown(ai_reply)
        
        return jsonify({
            'reply': ai_reply,
            'reply_html': formatted_reply,
            'session_id': chat_session.id,
            'message_id': ai_msg.id,
            'language': language
        }), 200
        
    except Exception as e:
        print(f"Chat error: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500

# ====================================================================
# USER PROFILE ROUTES
# ====================================================================

@app.route('/api/profile', methods=['GET'])
@login_required
def get_profile():
    user = get_user()
    stats = {
        'total_sessions': ChatSession.query.filter_by(user_id=user.id).count(),
        'total_messages': ChatMessage.query.join(ChatSession).filter(ChatSession.user_id == user.id).count(),
        'member_since': user.created_at.isoformat()
    }
    return jsonify({
        'user': user.to_dict(),
        'stats': stats
    }), 200

@app.route('/api/profile', methods=['PUT'])
@login_required
def update_profile():
    user = get_user()
    data = request.json
    
    if 'email' in data:
        email = data['email'].strip()
        if re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
            if not User.query.filter(User.email == email, User.id != user.id).first():
                user.email = email
    
    if 'password' in data and data['password']:
        if len(data['password']) >= 6:
            user.set_password(data['password'])
    
    db.session.commit()
    return jsonify({'message': 'Profile updated', 'user': user.to_dict()}), 200

# ====================================================================
# STATS ROUTE
# ====================================================================

@app.route('/api/stats', methods=['GET'])
def get_stats():
    total_users = User.query.count()
    total_messages = ChatMessage.query.count()
    active_sessions = ChatSession.query.filter(
        ChatSession.updated_at > datetime.utcnow() - timedelta(hours=24)
    ).count()
    
    return jsonify({
        'total_users': total_users,
        'total_messages': total_messages,
        'active_sessions': active_sessions,
        'openai_configured': bool(openai_client)
    }), 200

# ====================================================================
# FRONTEND ROUTES
# ====================================================================

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

# ====================================================================
# COMPLETE HTML/CSS/JS FRONTEND (Embedded)
# ====================================================================

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=yes">
    <title>Dark Wave AI - Next Generation AI Chatbot</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github-dark.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        :root {
            --primary: #00d4ff;
            --primary-dark: #0099cc;
            --secondary: #7b2cbf;
            --dark: #0a0a2a;
            --darker: #050514;
            --light: #f0f0f0;
            --gray: #8a8a8a;
            --success: #00ff88;
            --error: #ff4444;
            --warning: #ffaa00;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, var(--dark) 0%, var(--darker) 100%);
            color: var(--light);
            min-height: 100vh;
            overflow-x: hidden;
        }

        /* ===== AUTH STYLES ===== */
        .auth-overlay {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.95);
            backdrop-filter: blur(20px);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 2000;
            animation: fadeIn 0.5s ease;
        }

        .auth-card {
            background: linear-gradient(135deg, rgba(20, 20, 50, 0.95), rgba(10, 10, 30, 0.98));
            border-radius: 30px;
            padding: 40px;
            width: 90%;
            max-width: 450px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5), 0 0 0 1px rgba(0, 212, 255, 0.2);
            animation: slideUp 0.5s ease;
        }

        .auth-card h2 {
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            -webkit-background-clip: text;
            background-clip: text;
            color: transparent;
            text-align: center;
            margin-bottom: 30px;
            font-size: 28px;
        }

        .auth-card input {
            width: 100%;
            padding: 14px 18px;
            margin: 10px 0;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(0, 212, 255, 0.3);
            border-radius: 15px;
            color: white;
            font-size: 16px;
            transition: all 0.3s;
        }

        .auth-card input:focus {
            outline: none;
            border-color: var(--primary);
            box-shadow: 0 0 15px rgba(0, 212, 255, 0.2);
        }

        .auth-card button {
            width: 100%;
            padding: 14px;
            margin-top: 20px;
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            border: none;
            border-radius: 15px;
            color: white;
            font-weight: bold;
            font-size: 16px;
            cursor: pointer;
            transition: all 0.3s;
        }

        .auth-card button:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 25px rgba(0, 212, 255, 0.3);
        }

        .auth-card p {
            text-align: center;
            margin-top: 20px;
            color: var(--gray);
        }

        .auth-card a {
            color: var(--primary);
            cursor: pointer;
            text-decoration: none;
        }

        .auth-card a:hover {
            text-decoration: underline;
        }
 
 /* ===== MAIN APP STYLES ===== */
        .app-container {
            display: none;
            height: 100vh;
            overflow: hidden;
        }

        /* Sidebar */
        .sidebar {
            position: fixed;
            left: 0;
            top: 0;
            width: 300px;
            height: 100vh;
            background: linear-gradient(180deg, rgba(10, 10, 30, 0.98), rgba(5, 5, 20, 0.98));
            backdrop-filter: blur(10px);
            border-right: 1px solid rgba(0, 212, 255, 0.2);
            transform: translateX(-100%);
            transition: transform 0.3s ease;
            z-index: 1000;
            display: flex;
            flex-direction: column;
        }

        .sidebar.open {
            transform: translateX(0);
        }

        .sidebar-header {
            padding: 20px;
            border-bottom: 1px solid rgba(0, 212, 255, 0.2);
        }

        .sidebar-header h3 {
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            -webkit-background-clip: text;
            background-clip: text;
            color: transparent;
        }

        .new-chat-btn {
            width: 100%;
            padding: 12px;
            margin: 15px;
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            border: none;
            border-radius: 12px;
            color: white;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s;
        }

        .sessions-list {
            flex: 1;
            overflow-y: auto;
            padding: 10px;
        }

        .session-item {
            padding: 12px;
            margin: 5px 0;
            background: rgba(255, 255, 255, 0.03);
            border-radius: 10px;
            cursor: pointer;
            transition: all 0.3s;
        }

        .session-item:hover {
            background: rgba(0, 212, 255, 0.1);
            transform: translateX(5px);
        }

        .session-item.active {
            background: linear-gradient(135deg, rgba(0, 212, 255, 0.2), rgba(123, 44, 191, 0.2));
            border-left: 3px solid var(--primary);
        }

        .session-title {
            font-weight: bold;
            margin-bottom: 5px;
        }

        .session-date {
            font-size: 11px;
            color: var(--gray);
        }

        /* Main Chat Area */
        .main-chat {
            height: 100vh;
            display: flex;
            flex-direction: column;
            margin-left: 0;
            transition: margin-left 0.3s;
        }

        .main-chat.sidebar-open {
            margin-left: 0;
        }

        .chat-header {
            background: linear-gradient(135deg, rgba(10, 10, 30, 0.95), rgba(5, 5, 20, 0.95));
            backdrop-filter: blur(10px);
            padding: 15px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid rgba(0, 212, 255, 0.2);
            position: sticky;
            top: 0;
            z-index: 100;
        }

        .menu-toggle {
            background: none;
            border: none;
            color: var(--primary);
            font-size: 24px;
            cursor: pointer;
        }

        .logo {
            font-size: 20px;
            font-weight: bold;
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            -webkit-background-clip: text;
            background-clip: text;
            color: transparent;
        }

        .user-menu {
            display: flex;
            gap: 15px;
            align-items: center;
        }

        .user-avatar {
            width: 40px;
            height: 40px;
            border-radius: 50%;
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
        }

        /* Messages Area */
        .messages-container {
            flex: 1;
            overflow-y: auto;
            padding: 20px;
        }

        .message {
            display: flex;
            margin-bottom: 20px;
            animation: fadeIn 0.3s ease;
        }

        .message.user {
            justify-content: flex-end;
        }

        .message-content {
            max-width: 70%;
            padding: 12px 18px;
            border-radius: 20px;
            word-wrap: break-word;
        }

        .message.user .message-content {
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            color: white;
            border-bottom-right-radius: 5px;
        }

        .message.assistant .message-content {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(0, 212, 255, 0.2);
            border-bottom-left-radius: 5px;
        }

        .message-content pre {
            background: #1e1e1e;
            padding: 10px;
            border-radius: 8px;
            overflow-x: auto;
            margin: 10px 0;
        }

        .message-content code {
            background: #1e1e1e;
            padding: 2px 5px;
            border-radius: 4px;
            font-family: 'Courier New', monospace;
        }

        /* Input Area */
        .input-container {
            background: linear-gradient(135deg, rgba(10, 10, 30, 0.95), rgba(5, 5, 20, 0.95));
            backdrop-filter: blur(10px);
            padding: 20px;
            border-top: 1px solid rgba(0, 212, 255, 0.2);
        }

        .input-wrapper {
            display: flex;
            gap: 10px;
            align-items: center;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 25px;
            padding: 5px 15px;
            border: 1px solid rgba(0, 212, 255, 0.3);
        }

        .input-wrapper input {
            flex: 1;
            background: none;
            border: none;
            color: white;
            padding: 12px;
            font-size: 16px;
            outline: none;
        }

        .input-wrapper button {
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            border: none;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            color: white;
            cursor: pointer;
            transition: all 0.3s;
        }

        .input-wrapper button:hover {
            transform: scale(1.05);
        }

        /* Typing Indicator */
        .typing-indicator {
            display: inline-flex;
            gap: 5px;
            padding: 10px 15px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 20px;
        }

        .typing-indicator span {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: var(--primary);
            animation: typing 1.4s infinite;
        }

        .typing-indicator span:nth-child(2) {
            animation-delay: 0.2s;
        }

        .typing-indicator span:nth-child(3) {
            animation-delay: 0.4s;
        }

        @keyframes typing {
            0%, 60%, 100% {
                transform: translateY(0);
                opacity: 0.4;
            }
            30% {
                transform: translateY(-10px);
                opacity: 1;
            }
        }

        @keyframes fadeIn {
            from {
                opacity: 0;
                transform: translateY(20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        @keyframes slideUp {
            from {
                opacity: 0;
                transform: translateY(50px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        /* Responsive */
        @media (min-width: 768px) {
            .sidebar {
                transform: translateX(0);
            }
            .main-chat.sidebar-open {
                margin-left: 300px;
            }
            .menu-toggle {
                display: none;
            }
        }

        @media (max-width: 767px) {
            .message-content {
                max-width: 85%;
            }
        }

        /* Loading Spinner */
        .spinner {
            width: 40px;
            height: 40px;
            border: 3px solid rgba(0, 212, 255, 0.3);
            border-top-color: var(--primary);
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 20px auto;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        /* Toast Notifications */
        .toast {
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            color: white;
            padding: 12px 20px;
            border-radius: 10px;
            z-index: 2000;
            animation: slideInRight 0.3s ease;
        }

        @keyframes slideInRight {
            from {
                transform: translateX(100%);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
    </style>
</head>
<body>

<!-- Auth Section -->
<div id="authOverlay" class="auth-overlay">
    <div class="auth-card">
        <h2>🌊 Dark Wave AI</h2>
        <div id="loginForm">
            <input type="text" id="loginUsername" placeholder="Username" autocomplete="off">
            <input type="password" id="loginPassword" placeholder="Password">
            <button onclick="login()">Login</button>
            <p>Don't have an account? <a onclick="showRegister()">Register</a></p>
        </div>
        <div id="registerForm" style="display:none">
            <input type="text" id="regUsername" placeholder="Username" autocomplete="off">
            <input type="email" id="regEmail" placeholder="Email" autocomplete="off">
            <input type="password" id="regPassword" placeholder="Password (min 6 chars)">
            <button onclick="register()">Register</button>
            <p>Already have an account? <a onclick="showLogin()">Login</a></p>
        </div>
    </div>
</div>

<!-- Main App -->
<div id="appContainer" class="app-container">
    <!-- Sidebar -->
    <div id="sidebar" class="sidebar">
        <div class="sidebar-header">
            <h3>🌊 Dark Wave AI</h3>
        </div>
        <button class="new-chat-btn" onclick="createNewChat()">
            <i class="fas fa-plus"></i> New Chat
        </button>
        <div id="sessionsList" class="sessions-list"></div>
    </div>

    <!-- Main Chat -->
    <div id="mainChat" class="main-chat">
        <div class="chat-header">
            <button class="menu-toggle" onclick="toggleSidebar()">
                <i class="fas fa-bars"></i>
            </button>
            <div class="logo">Dark Wave AI</div>
            <div class="user-menu">
                <div class="user-avatar" onclick="logout()">
                    <i class="fas fa-user"></i>
                </div>
            </div>
        </div>

        <div id="messagesContainer" class="messages-container"></div>

        <div class="input-container">
            <div class="input-wrapper">
                <input type="text" id="messageInput" placeholder="Type your message..." 
                       onkeypress="if(event.key==='Enter') sendMessage()">
                <button onclick="sendMessage()">
                    <i class="fas fa-paper-plane"></i>
                </button>
            </div>
        </div>
    </div>
</div>

<script>
    // ====================================================================
    // STATE MANAGEMENT
    // ====================================================================
    let currentUser = null;
    let currentSession = null;
    let sessions = [];
    let isTyping = false;

    // ====================================================================
    // AUTHENTICATION
    // ====================================================================
    async function checkAuth() {
        try {
            const res = await fetch('/api/check_auth', {
                credentials: 'include'
            });
            const data = await res.json();
            if (data.authenticated) {
                currentUser = data.user;
                document.getElementById('authOverlay').style.display = 'none';
                document.getElementById('appContainer').style.display = 'flex';
                loadSessions();
            }
        } catch (error) {
            console.error('Auth check failed:', error);
        }
    }

    async function login() {
        const username = document.getElementById('loginUsername').value.trim();
        const password = document.getElementById('loginPassword').value;
        
        if (!username || !password) {
            showToast('Please enter username and password');
            return;
        }
        
        try {
            const res = await fetch('/api/login', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                credentials: 'include',
                body: JSON.stringify({username, password})
            });
            const data = await res.json();
            if (res.ok) {
                await checkAuth();
                showToast('Login successful!');
            } else {
                showToast(data.error);
            }
        } catch (error) {
            showToast('Network error');
        }
    }

    async function register() {
        const username = document.getElementById('regUsername').value.trim();
        const email = document.getElementById('regEmail').value.trim();
        const password = document.getElementById('regPassword').value;
        
        if (!username || !email || !password) {
            showToast('Please fill all fields');
            return;
        }
        
        if (password.length < 6) {
            showToast('Password must be at least 6 characters');
            return;
        }
        
        try {
            const res = await fetch('/api/register', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({username, email, password})
            });
            const data = await res.json();
            if (res.ok) {
                showToast('Registration successful! Please login.');
                showLogin();
            } else {
                showToast(data.error);
            }
        } catch (error) {
            showToast('Network error');
        }
    }

    async function logout() {
        await fetch('/api/logout', {method: 'POST', credentials: 'include'});
        location.reload();
    }

    function showLogin() {
        document.getElementById('loginForm').style.display = 'block';
        document.getElementById('registerForm').style.display = 'none';
    }

    function showRegister() {
        document.getElementById('loginForm').style.display = 'none';
        document.getElementById('registerForm').style.display = 'block';
    }

    // ====================================================================
    // SESSIONS MANAGEMENT
    // ====================================================================
    async function loadSessions() {
        try {
            const res = await fetch('/api/sessions', {credentials: 'include'});
            const data = await res.json();
            sessions = data.sessions;
            renderSessions();
            if (sessions.length > 0 && !currentSession) {
                loadSession(sessions[0].id);
            } else if (sessions.length === 0) {
                createNewChat();
            }
        } catch (error) {
            console.error('Failed to load sessions:', error);
        }
    }

    async function createNewChat() {
        try {
            const res = await fetch('/api/sessions', {
                method: 'POST',
                credentials: 'include',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({})
            });
            const data = await res.json();
            await loadSessions();
            loadSession(data.id);
        } catch (error) {
            console.error('Failed to create session:', error);
        }
    }

    async function loadSession(sessionId) {
        currentSession = sessionId;
        try {
            const res = await fetch(`/api/sessions/${sessionId}/messages`, {credentials: 'include'});
            const data = await res.json();
            renderMessages(data.messages);
            renderSessions();
        } catch (error) {
            console.error('Failed to load messages:', error);
        }
    }

    function renderSessions() {
        const container = document.getElementById('sessionsList');
        container.innerHTML = sessions.map(s => `
            <div class="session-item ${currentSession === s.id ? 'active' : ''}" 
                 onclick="loadSession(${s.id})">
                <div class="session-title">${escapeHtml(s.title)}</div>
                <div class="session-date">${new Date(s.updated_at).toLocaleDateString()}</div>
            </div>
        `).join('');
    }

    // ====================================================================
    // CHAT FUNCTIONS
    // ====================================================================
    async function sendMessage() {
        if (isTyping) return;
        
        const input = document.getElementById('messageInput');
        const message = input.value.trim();
        
        if (!message || !currentSession) return;
        
        // Add user message to UI
        addMessageToUI('user', message);
        input.value = '';
        
        // Show typing indicator
        showTypingIndicator();
        isTyping = true;
        
        try {
            const res = await fetch('/api/chat', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                credentials: 'include',
                body: JSON.stringify({
                    message: message,
                    session_id: currentSession
                })
            });
            const data = await res.json();
            
            removeTypingIndicator();
            
            if (data.error) {
                addMessageToUI('assistant', 'Error: ' + data.error);
            } else {
                addMessageToUI('assistant', data.reply, data.reply_html);
                // Refresh session list to update title
                loadSessions();
            }
        } catch (error) {
            removeTypingIndicator();
            addMessageToUI('assistant', 'Network error. Please try again.');
        } finally {
            isTyping = false;
        }
    }

    function addMessageToUI(role, content, htmlContent = null) {
        const container = document.getElementById('messagesContainer');
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}`;
        
        const displayContent = htmlContent || escapeHtml(content);
        messageDiv.innerHTML = `
            <div class="message-content">
                ${role === 'assistant' ? '<i class="fas fa-robot"></i> ' : '<i class="fas fa-user"></i> '}
                ${displayContent}
            </div>
        `;
        
        container.appendChild(messageDiv);
        container.scrollTop = container.scrollHeight;
        
        // Highlight code blocks
        if (typeof hljs !== 'undefined') {
            messageDiv.querySelectorAll('pre code').forEach((block) => {
                hljs.highlightElement(block);
            });
        }
    }

    function showTypingIndicator() {
        const container = document.getElementById('messagesContainer');
        const indicator = document.createElement('div');
        indicator.className = 'message assistant';
        indicator.id = 'typingIndicator';
        indicator.innerHTML = `
            <div class="message-content">
                <div class="typing-indicator">
                    <span></span><span></span><span></span>
                </div>
            </div>
        `;
        container.appendChild(indicator);
        container.scrollTop = container.scrollHeight;
    }

    function removeTypingIndicator() {
        const indicator = document.getElementById('typingIndicator');
        if (indicator) indicator.remove();
    }

    function renderMessages(messages) {
        const container = document.getElementById('messagesContainer');
        container.innerHTML = '';
        messages.forEach(msg => {
            addMessageToUI(msg.role, msg.content);
        });
    }

    // ====================================================================
    // UI HELPERS
    // ====================================================================
    function toggleSidebar() {
        const sidebar = document.getElementById('sidebar');
        sidebar.classList.toggle('open');
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function showToast(message) {
        const toast = document.createElement('div');
        toast.className = 'toast';
        toast.innerHTML = message;
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 3000);
    }

    // ====================================================================
    // INITIALIZATION
    // ====================================================================
    checkAuth();
    
    // Marked.js configuration
    if (typeof marked !== 'undefined') {
        marked.setOptions({
            highlight: function(code, lang) {
                if (lang && hljs.getLanguage(lang)) {
                    return hljs.highlight(code, {language: lang}).value;
                }
                return hljs.highlightAuto(code).value;
            }
        });
    }
</script>
</body>
</html>
'''

# ====================================================================
# RUN APPLICATION
# ====================================================================

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_ENV') == 'development'
    
    print('=' * 60)
    print('🌊 DARK WAVE AI - PRODUCTION READY')
    print('=' * 60)
    print(f'OpenAI: {"Configured" if openai_client else "Demo Mode"}')
    print(f'Server: http://localhost:{port}')
    print(f'Debug: {debug}')
    print('=' * 60)
    
    app.run(host='0.0.0.0', port=port, debug