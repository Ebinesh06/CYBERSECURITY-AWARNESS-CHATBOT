import { Component, OnInit, ViewChild, ElementRef, ChangeDetectorRef, AfterViewChecked, HostListener } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';

interface Message {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
  timestamp: Date;
}

interface ChatSession {
  id: string;
  title: string;
  lastActive: string;
  messageCount: number;
}

const API = 'http://127.0.0.1:8000';

@Component({
  selector: 'app-chat',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './chat.html',
  styleUrls: ['./chat.css']
})
export class ChatComponent implements OnInit, AfterViewChecked {
  @ViewChild('messagesContainer') messagesContainer!: ElementRef;
  @ViewChild('messageInput') messageInput!: ElementRef;

  messages: Message[] = [];
  userInput = '';
  isLoading = false;
  sidebarOpen = true;
  username = 'User';
  currentSessionId = '';
  chatSessions: ChatSession[] = [];
  editingSessionId: string | null = null;
  editTitle = '';
  private shouldScroll = false;
  private token = '';

  constructor(private router: Router, private cdr: ChangeDetectorRef) {}

  ngOnInit() {
    this.token = localStorage.getItem('token') || '';
    if (!this.token) {
      this.router.navigate(['/user-login']);
      return;
    }
    this.username = localStorage.getItem('username') || 'User';
    this.generateSessionId();
    this.loadSessionsFromServer();

    // Responsive: close sidebar on small screens
    if (window.innerWidth < 768) {
      this.sidebarOpen = false;
    }
  }

  ngAfterViewChecked() {
    if (this.shouldScroll) {
      this.scrollToBottom();
      this.shouldScroll = false;
    }
  }

  @HostListener('window:resize')
  onResize() {
    if (window.innerWidth < 768) {
      this.sidebarOpen = false;
    }
  }

  private authHeaders(): Record<string, string> {
    return {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${this.token}`
    };
  }

  generateSessionId() {
    this.currentSessionId = 'sess_' + Date.now() + '_' + Math.random().toString(36).substr(2, 6);
  }

  // --- SERVER SESSION MANAGEMENT ---

  async loadSessionsFromServer() {
    try {
      const res = await fetch(`${API}/chat/sessions`, { headers: this.authHeaders() });
      if (res.ok) {
        this.chatSessions = await res.json();
        this.cdr.detectChanges();
      }
    } catch (e) {
      console.error('Failed to load sessions:', e);
    }
  }

  async loadSession(sessionId: string) {
    try {
      const res = await fetch(`${API}/chat/sessions/${sessionId}`, { headers: this.authHeaders() });
      if (!res.ok) return;
      const data = await res.json();
      this.messages = data.map((m: any) => ({
        id: m.id,
        sender: m.role === 'user' ? 'user' : 'assistant',
        text: m.content,
        timestamp: new Date(m.created_at)
      }));
      this.currentSessionId = sessionId;
      this.shouldScroll = true;
      this.cdr.detectChanges();

      // Close sidebar on mobile after selecting
      if (window.innerWidth < 768) {
        this.sidebarOpen = false;
      }
    } catch (e) {
      console.error('Failed to load session:', e);
    }
  }

  async deleteSession(sessionId: string, event: Event) {
    event.stopPropagation();
    try {
      await fetch(`${API}/chat/sessions/${sessionId}`, {
        method: 'DELETE',
        headers: this.authHeaders()
      });
      this.chatSessions = this.chatSessions.filter(s => s.id !== sessionId);
      if (this.currentSessionId === sessionId) {
        this.messages = [];
        this.generateSessionId();
      }
      this.cdr.detectChanges();
    } catch (e) {
      console.error('Failed to delete session:', e);
    }
  }

  // --- CHAT ACTIONS ---

  startNewChat() {
    this.messages = [];
    this.generateSessionId();
    this.userInput = '';
    this.cdr.detectChanges();
    // Focus input
    setTimeout(() => this.messageInput?.nativeElement?.focus(), 100);
  }

  async sendMessage() {
    const userMsg = this.userInput.trim();
    if (!userMsg || this.isLoading) return;

    // User message
    this.messages.push({
      id: 'msg_' + Date.now(),
      sender: 'user',
      text: userMsg,
      timestamp: new Date()
    });
    this.userInput = '';
    this.isLoading = true;
    this.shouldScroll = true;
    this.cdr.detectChanges();

    // Auto-resize textarea back
    if (this.messageInput?.nativeElement) {
      this.messageInput.nativeElement.style.height = 'auto';
    }

    // Assistant placeholder
    const assistantMsg: Message = {
      id: 'msg_' + (Date.now() + 1),
      sender: 'assistant',
      text: '',
      timestamp: new Date()
    };
    this.messages.push(assistantMsg);
    this.cdr.detectChanges();

    try {
      const response = await fetch(`${API}/chat`, {
        method: 'POST',
        headers: this.authHeaders(),
        body: JSON.stringify({ message: userMsg, session_id: this.currentSessionId })
      });

      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      if (!response.body) throw new Error('No response body');

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        assistantMsg.text += decoder.decode(value, { stream: true });
        this.shouldScroll = true;
        this.cdr.detectChanges();
      }
    } catch (error) {
      assistantMsg.text = 'Sorry, I couldn\'t connect to the server. Please check that the backend is running and try again.';
      console.error('Stream error:', error);
    } finally {
      this.isLoading = false;
      this.shouldScroll = true;
      this.cdr.detectChanges();
      // Refresh sidebar sessions
      await this.loadSessionsFromServer();
    }
  }

  quickAsk(question: string) {
    this.userInput = question;
    this.sendMessage();
  }

  // --- INPUT HANDLING ---

  onKeydown(event: KeyboardEvent) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      this.sendMessage();
    }
  }

  autoResize(event: Event) {
    const el = event.target as HTMLTextAreaElement;
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 150) + 'px';
  }

  // --- UI HELPERS ---

  toggleSidebar() {
    this.sidebarOpen = !this.sidebarOpen;
  }

  logout() {
    localStorage.clear();
    this.router.navigate(['/user-login']);
  }

  getTimeLabel(session: ChatSession): string {
    if (!session.lastActive) return '';
    const d = new Date(session.lastActive);
    const now = new Date();
    const diff = now.getTime() - d.getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return 'Just now';
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    const days = Math.floor(hrs / 24);
    if (days === 1) return 'Yesterday';
    if (days < 7) return `${days}d ago`;
    return d.toLocaleDateString();
  }

  getInitial(): string {
    return this.username.charAt(0).toUpperCase();
  }

  trackBySessionId(index: number, session: ChatSession): string {
    return session.id;
  }

  trackByMessageId(index: number, msg: Message): string {
    return msg.id;
  }

  renderMarkdown(text: string): string {
    if (!text) return '';
    let html = text
      // Escape HTML to prevent XSS
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      // Headers: ### text → <h3>
      .replace(/^### (.+)$/gm, '<h3>$1</h3>')
      .replace(/^## (.+)$/gm, '<h2>$1</h2>')
      // Bold: **text** → <strong>
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      // Numbered lists: 1. text → <li>
      .replace(/^(\d+)\.\s+(.+)$/gm, '<li><span class="list-num">$1.</span> $2</li>')
      // Paragraphs: double newline
      .replace(/\n\n/g, '</p><p>')
      // Single newlines within a paragraph
      .replace(/\n/g, '<br>');
    // Wrap in paragraph
    html = '<p>' + html + '</p>';
    // Clean up empty paragraphs
    html = html.replace(/<p><\/p>/g, '').replace(/<p>(<h[23]>)/g, '$1').replace(/(<\/h[23]>)<\/p>/g, '$1');
    // Wrap consecutive <li> in <ol>
    html = html.replace(/(<li>.*?<\/li>(?:<br>)?)+/g, (match) => {
      const cleaned = match.replace(/<br>/g, '');
      return '<ol>' + cleaned + '</ol>';
    });
    return html;
  }

  private scrollToBottom() {
    try {
      const el = this.messagesContainer?.nativeElement;
      if (el) el.scrollTop = el.scrollHeight;
    } catch (_) {}
  }
}
