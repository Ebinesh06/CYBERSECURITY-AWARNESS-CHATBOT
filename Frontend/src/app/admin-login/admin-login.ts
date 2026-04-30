import { Component, OnDestroy, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../environments/environment';

const MAX_ATTEMPTS = 5;
const LOCKOUT_SECONDS = 300;
const SESSION_TIMEOUT_MINUTES = 30;

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
  mfaCode = '';
  mfaRequired = false;
  mfaTokenTemp = '';
  showMfaSetup = false;
  mfaSecret = '';
  qrCodeUrl = '';
  
  isLoading = false;
  errorMessage = '';
  sessionMessage = '';
  showPassword = false;
  
  failedAttempts = 0;
  isLockedOut = false;
  lockoutCountdown = 0;
  
  trustDevice = false;
  deviceName = '';
  
  currentYear = new Date().getFullYear();
  private lockoutTimer?: ReturnType<typeof setInterval>;
  private sessionTimeout?: ReturnType<typeof setTimeout>;
  private apiUrl = environment.apiUrl;

  constructor(private router: Router, private http: HttpClient) {}

  ngOnInit() {
    const reason = localStorage.getItem('adminLogoutReason');
    if (reason) {
      this.sessionMessage = reason;
      localStorage.removeItem('adminLogoutReason');
    }

    const lockoutUntil = Number(sessionStorage.getItem('adminLockoutUntil') || 0);
    this.failedAttempts = Number(sessionStorage.getItem('adminFailedAttempts') || 0);
    
    if (lockoutUntil > Date.now()) {
      this.startLockoutCountdown(Math.ceil((lockoutUntil - Date.now()) / 1000));
    }
  }

  ngOnDestroy() {
    if (this.lockoutTimer) clearInterval(this.lockoutTimer);
    if (this.sessionTimeout) clearTimeout(this.sessionTimeout);
  }

  togglePassword() {
    this.showPassword = !this.showPassword;
  }

  login() {
    if (this.isLockedOut) return;
    if (!this.username.trim() || !this.password.trim()) {
      this.errorMessage = 'Username and password required.';
      return;
    }

    this.isLoading = true;
    this.errorMessage = '';

    this.http.post<any>(`${this.apiUrl}/auth/admin-login`, {
      username: this.username.trim(),
      password: this.password.trim(),
      device_fingerprint: this.generateDeviceFingerprint(),
      ip_address: 'auto-detect'
    }).subscribe({
      next: (res) => {
        if (res.requires_mfa) {
          this.mfaRequired = true;
          this.mfaTokenTemp = res.mfa_token;
          this.isLoading = false;
          this.errorMessage = 'MFA code required.';
          return;
        }
        this.clearLockout();
        localStorage.setItem('access_token', res.access_token);
        localStorage.setItem('username', res.username);
        this.isLoading = false;
        this.router.navigate(['/admin-shell/dashboard']);
      },
      error: (err) => {
        this.isLoading = false;
        this.recordFailedAttempt();
        this.errorMessage = err.status === 423 ? 'Account locked.' : 'Login failed.';
      }
    });
  }

  verifyMfa() {
    if (!this.mfaCode || this.mfaCode.length !== 6) {
      this.errorMessage = 'Enter 6-digit code.';
      return;
    }

    this.isLoading = true;
    this.http.post<any>(`${this.apiUrl}/auth/verify-mfa`, {
      mfa_token: this.mfaTokenTemp,
      mfa_code: this.mfaCode,
      trust_device: this.trustDevice,
      device_name: this.deviceName || 'Device'
    }).subscribe({
      next: (res) => {
        this.clearLockout();
        localStorage.setItem('access_token', res.access_token);
        localStorage.setItem('username', res.username);
        this.isLoading = false;
        this.mfaRequired = false;
        this.router.navigate(['/admin-shell/dashboard']);
      },
      error: () => {
        this.isLoading = false;
        this.recordFailedAttempt();
        this.errorMessage = 'MFA failed.';
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

  private clearLockout() {
    this.isLockedOut = false;
    this.failedAttempts = 0;
    sessionStorage.removeItem('adminFailedAttempts');
    sessionStorage.removeItem('adminLockoutUntil');
    if (this.lockoutTimer) clearInterval(this.lockoutTimer);
  }

  private startLockoutCountdown(seconds: number) {
    this.isLockedOut = true;
    this.lockoutCountdown = seconds;
    this.lockoutTimer = setInterval(() => {
      this.lockoutCountdown--;
      if (this.lockoutCountdown <= 0) {
        if (this.lockoutTimer) clearInterval(this.lockoutTimer);
        this.clearLockout();
      }
    }, 1000);
  }

  private generateDeviceFingerprint(): string {
    const fp = `${navigator.userAgent}${navigator.language}${new Date().getTimezoneOffset()}`;
    let hash = 0;
    for (let i = 0; i < fp.length; i++) {
      const char = fp.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
    }
    return Math.abs(hash).toString(16);
  }

  setupMfa() {
    this.isLoading = true;
    this.errorMessage = '';
    this.http.post<any>(`${this.apiUrl}/auth/setup-mfa`, {
      username: this.username
    }).subscribe({
      next: (res) => {
        this.isLoading = false;
        this.showMfaSetup = true;
        this.mfaSecret = res.mfa_secret;
        this.qrCodeUrl = res.qr_code_url;
      },
      error: () => {
        this.isLoading = false;
        this.errorMessage = 'Failed to setup MFA.';
      }
    });
  }

  confirmMfaSetup() {
    if (!this.mfaCode || this.mfaCode.length !== 6) {
      this.errorMessage = 'Enter 6-digit code.';
      return;
    }
    this.isLoading = true;
    this.http.post<any>(`${this.apiUrl}/auth/confirm-mfa-setup`, {
      username: this.username,
      mfa_code: this.mfaCode
    }).subscribe({
      next: () => {
        this.isLoading = false;
        this.showMfaSetup = false;
        this.mfaCode = '';
        alert('MFA enabled!');
      },
      error: () => {
        this.isLoading = false;
        this.errorMessage = 'Invalid code.';
      }
    });
  }

  copyToClipboard(text: string) {
    navigator.clipboard.writeText(text).then(() => {
      alert('Copied!');
    });
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
