const API_BASE = window.API_BASE || 'http://127.0.0.1:8000';

const chatListEl = document.getElementById('chatList');
const messagesEl = document.getElementById('messages');
const composerEl = document.getElementById('composer');
const inputEl = document.getElementById('messageInput');
const sendBtnEl = composerEl.querySelector('.send-btn');
const newChatBtn = document.getElementById('newChatBtn');
const tempChatBtn = document.getElementById('tempChatBtn');
const modeBadgeEl = document.getElementById('modeBadge');

let activeChatId = null;
let isTemporaryChat = false;
let localMessages = [];
let isBusy = false;
let typingEl = null;
const GREETING = 'Hello, Welcome to MediaFireWall, How can I help you today?';

function updateModeBadge() {
  if (!modeBadgeEl) return;
  modeBadgeEl.textContent = isTemporaryChat ? 'Temporary' : 'Persistent';
}

/**
 * Downloads a file programmatically to avoid navigation issues.
 * @param {string} url - The URL to download.
 * @param {string} filename - The filename to save as.
 */
async function triggerDownload(url, filename) {
  try {
    const response = await fetch(url);
    if (!response.ok) throw new Error('Network response was not ok');
    const blob = await response.blob();
    const blobUrl = window.URL.createObjectURL(blob);

    const a = document.createElement('a');
    a.style.display = 'none';
    a.href = blobUrl;
    a.download = filename; // Force download attribute
    document.body.appendChild(a);
    a.click();

    // Clean up
    window.URL.revokeObjectURL(blobUrl);
    document.body.removeChild(a);
  } catch (err) {
    console.error('Download failed:', err);
    alert('Failed to download report. Please try again.');
  }
}

// Global click handler for download buttons to intercept navigation
document.addEventListener('click', (e) => {
  if (e.target && e.target.classList.contains('download-btn')) {
    e.preventDefault(); // STOP navigation
    const url = e.target.href;
    // Extract filename from URL last segement
    const filename = url.split('/').pop() || 'report.csv';
    triggerDownload(url, filename);
  }
});

function formatMessageContent(raw) {
  let linked = raw;

  // 1. Check for Markdown links [Label](URL)
  const mdRegex = /\[([^\]]+)\]\(([^)]+)\)/g;

  if (mdRegex.test(raw)) {
    linked = raw.replace(mdRegex, (match, label, url) => {
      const isReport = url.includes('/reports/');
      const className = isReport ? 'download-btn' : '';
      // Ensure URL is absolute if it's a report
      const fullUrl = (isReport && url.startsWith('/')) ? `${API_BASE}${url}` : url;
      return `<a href="${fullUrl}" class="${className}">${label}</a>`;
    });
  } else {
    // 2. Fallback: Convert bare URLs
    linked = raw.replace(
      /(https?:\/\/[^\s]+|\/reports\/[^\s]+)/g,
      (match) => {
        const url = match;
        const isReport = url.startsWith('/reports/');
        const fullUrl = isReport ? `${API_BASE}${url}` : url;
        const className = isReport ? 'download-btn' : '';
        return `<a href="${fullUrl}" class="${className}">${url}</a>`;
      }
    );
  }
  return linked;
}

function typeText(element, text) {
  let index = 0;
  element.textContent = '';

  function nextChar() {
    if (index < text.length) {
      if (!document.body.contains(element)) return;
      element.textContent += text.charAt(index);
      index++;
      messagesEl.scrollTop = messagesEl.scrollHeight;
      const delay = Math.floor(Math.random() * 20) + 10;
      setTimeout(nextChar, delay);
    } else {
      // Post-typing: use formatter
      element.innerHTML = formatMessageContent(element.textContent);
    }
  }
  nextChar();
}

function renderMessages(messages) {
  messagesEl.innerHTML = '';
  for (let i = 0; i < messages.length; i += 1) {
    const m = messages[i];

    // Wrapper
    const div = document.createElement('div');
    div.className = `msg ${m.role}`;

    // Bubble
    const bubble = document.createElement('div');
    bubble.className = 'content-bubble';

    // Special case for greeting
    if (i === 0 && m.role === 'assistant' && (m.content === GREETING || m.content.includes('MediaFireWall'))) {
      div.classList.add('greeting-msg');
    }

    div.appendChild(bubble);
    messagesEl.appendChild(div);

    if (m.animate) {
      m.animate = false;
      typeText(bubble, m.content);
    } else {
      // Render formatting immediately for history
      bubble.innerHTML = formatMessageContent(m.content);
    }
  }
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function showTypingIndicator() {
  hideTypingIndicator();
  typingEl = document.createElement('div');
  typingEl.className = 'msg assistant';
  typingEl.innerHTML = '<div class="content-bubble typing"><span></span><span></span><span></span></div>';
  messagesEl.appendChild(typingEl);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function hideTypingIndicator() {
  if (typingEl) {
    typingEl.remove();
    typingEl = null;
  }
}

function updateSendEnabled() {
  if (!sendBtnEl) return;
  sendBtnEl.disabled = isBusy || !inputEl.value.trim();
}

function setBusy(nextBusy) {
  isBusy = nextBusy;
  inputEl.disabled = nextBusy;
  newChatBtn.disabled = nextBusy;
  tempChatBtn.disabled = nextBusy;
  composerEl.classList.toggle('is-busy', nextBusy);
  updateSendEnabled();
}

function renderChatList(chats) {
  chatListEl.innerHTML = '';
  for (const chat of chats) {
    const li = document.createElement('li');
    li.className = 'chat-row';

    const openBtn = document.createElement('button');
    openBtn.className = 'chat-open-btn';
    const prefix = chat.is_temporary ? '[Temp] ' : '';
    openBtn.textContent = `${prefix}${chat.title || 'Untitled Chat'}`;
    if (chat.chat_id === activeChatId) openBtn.classList.add('active');
    openBtn.onclick = async () => {
      isTemporaryChat = Boolean(chat.is_temporary);
      updateModeBadge();
      activeChatId = chat.chat_id;
      await loadMessages(chat.chat_id);
      await loadChats();
    };

    const deleteBtn = document.createElement('button');
    deleteBtn.className = 'chat-delete-btn';
    deleteBtn.title = 'Delete Chat';
    deleteBtn.innerHTML = `
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M3 6H5H21" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        <path d="M19 6V20C19 20.5304 18.7893 21.0391 18.4142 21.4142C18.0391 21.7893 17.5304 22 17 22H7C6.46957 22 5.96086 21.7893 5.58579 21.4142C5.21071 21.0391 5 20.5304 5 20V6M8 6V4C8 3.46957 8.21071 2.96086 8.58579 2.58579C8.96086 2.21071 9.46957 2 10 2H14C14.5304 2 15.0391 2.21071 15.4142 2.58579C15.7893 2.96086 16 3.46957 16 4V6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
    `;
    deleteBtn.onclick = async (e) => {
      e.stopPropagation();
      const ok = window.confirm('Delete this chat?');
      if (!ok) return;
      try {
        await api(`/chat/${chat.chat_id}`, { method: 'DELETE' });
        if (activeChatId === chat.chat_id) {
          resetToNew(false);
        }
        await loadChats();
      } catch (err) {
        alert(err.message);
      }
    };

    li.appendChild(openBtn);
    li.appendChild(deleteBtn);
    chatListEl.appendChild(li);
  }
}

async function api(path, options) {
  const res = await fetch(`${API_BASE}${path}`, options);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = data.detail;
    if (typeof detail === 'string') throw new Error(detail);
    if (Array.isArray(detail) && detail.length > 0) {
      const first = detail[0];
      throw new Error(first.msg || `HTTP ${res.status}`);
    }
    throw new Error(`HTTP ${res.status}`);
  }
  return data;
}

async function loadChats() {
  try {
    const chats = await api('/chat/list');
    renderChatList(chats);
  } catch (err) {
    console.error('loadChats:', err.message);
  }
}

async function loadMessages(chatId) {
  try {
    const data = await api(`/chat/${chatId}`);
    isTemporaryChat = Boolean(data.chat?.is_temporary);
    updateModeBadge();
    localMessages = data.messages || [];
    renderMessages(localMessages);
  } catch (err) {
    console.error('loadMessages:', err.message);
  }
}

function resetToNew(isTemp) {
  activeChatId = null;
  isTemporaryChat = isTemp;
  updateModeBadge();
  localMessages = [{ role: 'assistant', content: GREETING }];
  renderMessages(localMessages);
}

async function startChat(firstMessage) {
  if (isTemporaryChat) {
    localMessages = [{ role: 'user', content: firstMessage }];
    renderMessages(localMessages);
    showTypingIndicator();

    const data = await api('/chat/new', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ first_message: firstMessage, is_temporary: true })
    });
    activeChatId = data.chat_id;
    updateModeBadge();

    const reply = await api('/chat/temp/message', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ chat_id: activeChatId, content: firstMessage })
    });

    hideTypingIndicator();
    localMessages.push({ role: 'assistant', content: reply.response, animate: true });
    renderMessages(localMessages);
  } else {
    localMessages = [{ role: 'user', content: firstMessage }];
    renderMessages(localMessages);
    showTypingIndicator();

    const data = await api('/chat/new', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ first_message: firstMessage, is_temporary: false })
    });
    activeChatId = data.chat_id;
    updateModeBadge();

    hideTypingIndicator();
    localMessages.push({ role: 'assistant', content: data.response || '...', animate: true });
    renderMessages(localMessages);
    await loadChats();
  }
}

async function sendMessage(content) {
  if (!activeChatId) {
    await startChat(content);
    return;
  }

  if (isTemporaryChat) {
    localMessages.push({ role: 'user', content });
    renderMessages(localMessages);
    showTypingIndicator();

    const reply = await api('/chat/temp/message', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ chat_id: activeChatId, content })
    });

    hideTypingIndicator();
    localMessages.push({ role: 'assistant', content: reply.response, animate: true });
    renderMessages(localMessages);
  } else {
    localMessages.push({ role: 'user', content });
    renderMessages(localMessages);
    showTypingIndicator();
    const reply = await api(`/chat/${activeChatId}/message`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content, role: 'user' })
    });
    hideTypingIndicator();
    localMessages.push({ role: 'assistant', content: reply.response, animate: true });
    renderMessages(localMessages);
    await loadChats();
  }
}

composerEl.addEventListener('submit', async (e) => {
  e.preventDefault();
  if (isBusy) return;
  const text = inputEl.value.trim();
  if (!text) return;
  inputEl.value = '';
  updateSendEnabled();
  setBusy(true);
  try {
    await sendMessage(text);
  } catch (err) {
    console.error('sendMessage:', err.message);
    alert(err.message);
  } finally {
    hideTypingIndicator();
    setBusy(false);
    inputEl.focus();
  }
});

inputEl.addEventListener('input', updateSendEnabled);

newChatBtn.addEventListener('click', () => resetToNew(false));
tempChatBtn.addEventListener('click', () => resetToNew(true));

resetToNew(false);
loadChats();
updateSendEnabled();
