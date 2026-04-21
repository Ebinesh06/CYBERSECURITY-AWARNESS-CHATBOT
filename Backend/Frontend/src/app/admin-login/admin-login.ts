import { Component, OnDestroy, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { HttpClient } from '@angular/common/http';

const MAX_ATTEMPTS = 5;
const LOCKOUT_SECONDS = 30;

@Component({
  selector: 'app-admin-login',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './admin-login.html',
  styleUrls: ['./admin-login.css']
})
export class AdminLoginComponent implements OnInit, OnDestroy {
  username = '';
  password = '';
  isLoading = false;
  errorMessage = '';
  sessionMessage = '';

  showPassword = false;
  failedAttempts = 0;
  isLockedOut = false;
  lockoutCountdown = 0;
  loginAttemptLog: { time: string; outcome: 'success' | 'failed' }[] = [];

  currentYear = new Date().getFullYear();

  private lockoutTimer?: ReturnType<typeof setInterval>;

  constructor(private router: Router, private http: HttpClient) {}

  ngOnInit() {
    // Check if redirected due to session expiry or forced logout
    const reason = localStorage.getItem('adminLogoutReason');
    if (reason) {
      this.sessionMessage = reason;
      localStorage.removeItem('adminLogoutReason');
    }

    // Restore lockout state from sessionStorage (survives page refresh)
    const lockoutUntil = Number(sessionStorage.getItem('adminLockoutUntil') || 0);
    this.failedAttempts = Number(sessionStorage.getItem('adminFailedAttempts') || 0);
    if (lockoutUntil > Date.now()) {
      this.startLockoutCountdown(Math.ceil((lockoutUntil - Date.now()) / 1000));
    }
  }

  ngOnDestroy() {
    if (this.lockoutTimer) clearInterval(this.lockoutTimer);
  }

  togglePassword() {
    this.showPassword = !this.showPassword;
  }

  login() {
    if (this.isLockedOut) return;

    if (!this.username.trim() || !this.password.trim()) {
      this.errorMessage = 'Username and password are required.';
      return;
    }

    this.isLoading = true;
    this.errorMessage = '';
    this.sessionMessage = '';

    this.http.post<any>('http://127.0.0.1:8000/auth/login', {
      username: this.username.trim(),
      password: this.password.trim()
    }).subscribe({
      next: (res) => {
        if (res.role !== 'admin') {
          this.isLoading = false;
          this.recordFailedAttempt();
          this.errorMessage = 'Access denied. Admin privileges required.';
          return;
        }

        // Success — clear lockout state
        sessionStorage.removeItem('adminFailedAttempts');
        sessionStorage.removeItem('adminLockoutUntil');
        this.failedAttempts = 0;

        localStorage.setItem('token', res.access_token);
        localStorage.setItem('role', res.role);
        localStorage.setItem('username', res.username || this.username);
        this.isLoading = false;
        this.router.navigate(['/admin-shell/dashboard']);
      },
      error: () => {
        this.isLoading = false;
        this.recordFailedAttempt();
        const remaining = MAX_ATTEMPTS - this.failedAttempts;
        if (this.isLockedOut) {
          this.errorMessage = `Too many failed attempts. Account locked for ${LOCKOUT_SECONDS}s.`;
        } else {
          this.errorMessage = `Authentication failed. ${remaining} attempt${remaining !== 1 ? 's' : ''} remaining.`;
        }
      }
    });
  }

  private recordFailedAttempt() {
    this.failedAttempts++;
    sessionStorage.setItem('adminFailedAttempts', String(this.failedAttempts));
    if (this.failedAttempts >= MAX_ATTEMPTS) {
      const until = Date.now() + LOCKOUT_SECONDS * 1000;
      sessionStorage.setItem('adminLockoutUntil', String(until));
      this.startLockoutCountdown(LOCKOUT_SECONDS);
    }
  }

  private startLockoutCountdown(seconds: number) {
    this.isLockedOut = true;
    this.lockoutCountdown = seconds;
    this.lockoutTimer = setInterval(() => {
      this.lockoutCountdown--;
      if (this.lockoutCountdown <= 0) {
        clearInterval(this.lockoutTimer);
        this.isLockedOut = false;
        this.failedAttempts = 0;
        sessionStorage.removeItem('adminFailedAttempts');
        sessionStorage.removeItem('adminLockoutUntil');
        this.errorMessage = '';
      }
    }, 1000);
  }

  get attemptsBarWidth(): number {
    return Math.min((this.failedAttempts / MAX_ATTEMPTS) * 100, 100);
  }

  get attemptsBarColor(): string {
    if (this.failedAttempts >= MAX_ATTEMPTS) return '#ef4444';
    if (this.failedAttempts >= 3) return '#f59e0b';
    return '#22c55e';
  }
}
