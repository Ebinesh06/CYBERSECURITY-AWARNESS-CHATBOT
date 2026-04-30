import { Component, OnDestroy, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../environments/environment';

const SESSION_TIMEOUT_MS = 30 * 60 * 1000;
const WARNING_BEFORE_TIMEOUT_MS = 5 * 60 * 1000;

@Component({
  selector: 'app-user-login',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './user-login.html',
  styleUrls: ['./user-login.css']
})
export class UserLoginComponent implements OnInit, OnDestroy {
  // Expose to template
  SESSION_TIMEOUT_MS = SESSION_TIMEOUT_MS;
  Date = Date;
  
  private apiUrl = environment.apiUrl;

  // Login form
  username = '';
  password = '';
  isLoading = false;
  errorMessage = '';
  sessionMessage = '';
  isSignUp = false;

  // MFA flow
  mfaRequired = false;
  mfaCode = '';
  mfaTokenTemp = '';
  trustDevice = false;
  deviceName = 'User Device';
  showMfaSetup = false;
  mfaSecret = '';
  qrCodeUrl = '';
  setupMfaCode = '';

  // Password strength
  showPassword = false;
  showMfaPassword = false;
  passwordStrength = 0;

  // Account security
  failedAttempts = 0;
  isLockedOut = false;
  lockoutCountdown = 0;

  // Session management
  sessionTimeout = 0;
  sessionWarning = false;
  lastLoginTime = '';

  currentYear = new Date().getFullYear();

  private lockoutTimer?: ReturnType<typeof setInterval>;
  private sessionTimeoutTimer?: ReturnType<typeof setTimeout>;
  private sessionWarningTimer?: ReturnType<typeof setTimeout>;
  private inactivityTimer?: ReturnType<typeof setTimeout>;

  constructor(
    private router: Router,
    private http: HttpClient
  ) {}

  ngOnInit() {
    const reason = localStorage.getItem('userLogoutReason');
    if (reason) {
      this.sessionMessage = reason;
      localStorage.removeItem('userLogoutReason');
    }

    const lockoutUntil = Number(sessionStorage.getItem('userLockoutUntil') || 0);
    this.failedAttempts = Number(sessionStorage.getItem('userFailedAttempts') || 0);
    if (lockoutUntil > Date.now()) {
      this.startLockoutCountdown(Math.ceil((lockoutUntil - Date.now()) / 1000));
    }
  }

  ngOnDestroy() {
    this.clearTimers();
  }

  private clearTimers() {
    if (this.lockoutTimer) clearInterval(this.lockoutTimer);
    if (this.sessionTimeoutTimer) clearTimeout(this.sessionTimeoutTimer);
    if (this.sessionWarningTimer) clearTimeout(this.sessionWarningTimer);
    if (this.inactivityTimer) clearTimeout(this.inactivityTimer);
  }

  // ===== DEVICE FINGERPRINTING =====
  private generateDeviceFingerprint(): string {
    const userAgent = navigator.userAgent;
    const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
    const screen = `${window.screen.width}x${window.screen.height}`;
    const fingerprint = `${userAgent}|${timezone}|${screen}`;
    
    // Simple hash
    let hash = 0;
    for (let i = 0; i < fingerprint.length; i++) {
      const char = fingerprint.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash;
    }
    return Math.abs(hash).toString(16);
  }

  // ===== PASSWORD STRENGTH =====
  private validatePasswordStrength(password: string): { score: number; message: string } {
    if (password.length < 12) {
      return { score: 0, message: 'Minimum 12 characters required' };
    }
    if (!/[A-Z]/.test(password)) {
      return { score: 1, message: 'Add uppercase letter' };
    }
    if (!/[a-z]/.test(password)) {
      return { score: 2, message: 'Add lowercase letter' };
    }
    if (!/[0-9]/.test(password)) {
      return { score: 3, message: 'Add digit' };
    }
    if (!/[!@#$%^&*]/.test(password)) {
      return { score: 4, message: 'Add special character (!@#$%^&*)' };
    }
    return { score: 5, message: 'Strong password' };
  }

  updatePasswordStrength() {
    const validation = this.validatePasswordStrength(this.password);
    this.passwordStrength = validation.score;
  }

  togglePassword() {
    this.showPassword = !this.showPassword;
  }

  toggleSignUp() {
    this.isSignUp = !this.isSignUp;
    this.username = '';
    this.password = '';
    this.setupMfaCode = '';
    this.errorMessage = '';
    this.passwordStrength = 0;
  }

  // ===== LOGIN FLOW =====
  login() {
    if (this.isLockedOut) return;

    if (!this.username.trim() || !this.password.trim()) {
      this.errorMessage = 'Username and password are required.';
      return;
    }

    this.isLoading = true;
    this.errorMessage = '';
    this.sessionMessage = '';

    const deviceFingerprint = this.generateDeviceFingerprint();

    this.http.post<any>(`${this.apiUrl}/auth/login`, {
      username: this.username.trim(),
      password: this.password.trim(),
      device_fingerprint: deviceFingerprint,
      ip_address: 'auto-detect'
    }).subscribe({
      next: (res) => {
        this.handleLoginSuccess(res);
      },
      error: (err) => {
        this.handleLoginError(err);
      }
    });
  }

  private handleLoginSuccess(res: any) {
    sessionStorage.removeItem('userFailedAttempts');
    sessionStorage.removeItem('userLockoutUntil');
    this.failedAttempts = 0;

    if (res.mfa_required) {
      // MFA required
      this.mfaRequired = true;
      this.mfaTokenTemp = res.mfa_token;
      this.isLoading = false;
      if (res.force_mfa) {
        this.errorMessage = `Security alert: ${res.suspicious_reason || 'Suspicious activity detected'}. MFA verification required.`;
      }
    } else {
      // No MFA, login successful
      this.storeTokens(res);
      this.isLoading = false;
      this.startSessionTimeout();
      this.router.navigate(['/chat']);
    }
  }

  private handleLoginError(err: any) {
    this.isLoading = false;
    
    if (err.status === 423) {
      this.errorMessage = 'Account locked. Too many failed attempts. Try again later.';
      this.failedAttempts = 5;
      this.recordFailedAttempt();
    } else if (err.status === 429) {
      this.errorMessage = err.error?.detail || 'Too many login attempts. Please try again later.';
    } else {
      this.recordFailedAttempt();
      const remaining = 5 - this.failedAttempts;
      if (this.isLockedOut) {
        this.errorMessage = 'Account locked due to multiple failed attempts.';
      } else {
        this.errorMessage = `Authentication failed. ${remaining} attempt${remaining !== 1 ? 's' : ''} remaining.`;
      }
    }
  }

  // ===== SIGNUP FLOW =====
  signUp() {
    if (this.isLockedOut) return;

    if (!this.username.trim() || !this.password.trim()) {
      this.errorMessage = 'Username and password are required.';
      return;
    }

    const validation = this.validatePasswordStrength(this.password);
    if (validation.score < 5) {
      this.errorMessage = `Password requirement: ${validation.message}`;
      return;
    }

    this.isLoading = true;
    this.errorMessage = '';
    this.sessionMessage = '';

    const deviceFingerprint = this.generateDeviceFingerprint();

    this.http.post<any>(`${this.apiUrl}/auth/signup`, {
      username: this.username.trim(),
      password: this.password.trim(),
      device_fingerprint: deviceFingerprint,
      ip_address: 'auto-detect'
    }).subscribe({
      next: (res) => {
        sessionStorage.removeItem('userFailedAttempts');
        sessionStorage.removeItem('userLockoutUntil');
        this.failedAttempts = 0;

        this.storeTokens(res);
        this.isLoading = false;
        this.startSessionTimeout();
        this.router.navigate(['/chat']);
      },
      error: (err) => {
        this.isLoading = false;
        this.recordFailedAttempt();
        const remaining = 5 - this.failedAttempts;
        if (this.isLockedOut) {
          this.errorMessage = 'Too many attempts. Account locked.';
        } else {
          this.errorMessage = err.error?.detail || `Signup failed. ${remaining} attempt${remaining !== 1 ? 's' : ''} remaining.`;
        }
      }
    });
  }

  // ===== MFA VERIFICATION =====
  verifyMfa() {
    if (!this.mfaCode.trim() || this.mfaCode.length !== 6) {
      this.errorMessage = 'MFA code must be 6 digits.';
      return;
    }

    this.isLoading = true;
    this.errorMessage = '';

    this.http.post<any>(`${this.apiUrl}/auth/verify-mfa`, {
      mfa_token: this.mfaTokenTemp,
      mfa_code: this.mfaCode.trim(),
      trust_device: this.trustDevice,
      device_name: this.deviceName.trim() || 'User Device'
    }).subscribe({
      next: (res) => {
        this.storeTokens(res);
        this.isLoading = false;
        this.mfaRequired = false;
        this.mfaCode = '';
        this.startSessionTimeout();
        this.router.navigate(['/chat']);
      },
      error: (err) => {
        this.isLoading = false;
        this.errorMessage = err.error?.detail || 'Invalid MFA code. Please try again.';
      }
    });
  }

  backFromMfa() {
    this.mfaRequired = false;
    this.mfaCode = '';
    this.mfaTokenTemp = '';
    this.errorMessage = '';
    this.trustDevice = false;
    this.deviceName = 'User Device';
  }

  // ===== MFA SETUP =====
  initiateSetupMfa() {
    this.showMfaSetup = true;
    this.setupMfaCode = '';
    this.errorMessage = '';

    this.http.post<any>(`${this.apiUrl}/auth/user/setup-mfa`, {
      username: this.username.trim()
    }).subscribe({
      next: (res) => {
        this.mfaSecret = res.mfa_secret;
        this.qrCodeUrl = res.qr_code_url;
      },
      error: (err) => {
        this.errorMessage = err.error?.detail || 'Failed to setup MFA.';
        this.showMfaSetup = false;
      }
    });
  }

  confirmMfaSetup() {
    if (!this.setupMfaCode.trim() || this.setupMfaCode.length !== 6) {
      this.errorMessage = 'MFA code must be 6 digits.';
      return;
    }

    this.isLoading = true;
    this.errorMessage = '';

    this.http.post<any>(`${this.apiUrl}/auth/user/confirm-mfa`, {
      username: this.username.trim(),
      mfa_code: this.setupMfaCode.trim()
    }).subscribe({
      next: (res) => {
        this.isLoading = false;
        this.showMfaSetup = false;
        this.setupMfaCode = '';
        this.mfaSecret = '';
        this.qrCodeUrl = '';
        alert('MFA enabled successfully!');
        this.toggleSignUp();
      },
      error: (err) => {
        this.isLoading = false;
        this.errorMessage = err.error?.detail || 'Failed to confirm MFA setup.';
      }
    });
  }

  cancelMfaSetup() {
    this.showMfaSetup = false;
    this.setupMfaCode = '';
    this.mfaSecret = '';
    this.qrCodeUrl = '';
    this.errorMessage = '';
  }

  copyToClipboard(text: string) {
    navigator.clipboard.writeText(text).then(() => {
      alert('Copied to clipboard!');
    }).catch(() => {
      alert('Failed to copy');
    });
  }

  // ===== SESSION MANAGEMENT =====
  private storeTokens(res: any) {
    localStorage.setItem('token', res.access_token);
    localStorage.setItem('refreshToken', res.refresh_token);
    localStorage.setItem('role', res.role);
    localStorage.setItem('username', res.username || this.username);
    this.lastLoginTime = new Date().toLocaleString();
  }

  private startSessionTimeout() {
    this.clearTimers();

    // Warning timer (show warning 5 minutes before timeout)
    this.sessionWarningTimer = setTimeout(() => {
      this.sessionWarning = true;
      this.errorMessage = 'Your session will expire in 5 minutes due to inactivity.';
    }, SESSION_TIMEOUT_MS - WARNING_BEFORE_TIMEOUT_MS);

    // Logout timer
    this.sessionTimeoutTimer = setTimeout(() => {
      this.logout('Session expired due to inactivity');
    }, SESSION_TIMEOUT_MS);
  }

  logout(reason: string = 'Logged out successfully') {
    this.clearTimers();
    localStorage.removeItem('token');
    localStorage.removeItem('refreshToken');
    localStorage.removeItem('role');
    localStorage.removeItem('username');
    localStorage.setItem('userLogoutReason', reason);
    this.router.navigate(['/user-login']);
  }

  // ===== ACCOUNT LOCKOUT =====
  private recordFailedAttempt() {
    this.failedAttempts++;
    sessionStorage.setItem('userFailedAttempts', String(this.failedAttempts));
    if (this.failedAttempts >= 5) {
      const until = Date.now() + 5 * 60 * 1000; // 5 minute lockout
      sessionStorage.setItem('userLockoutUntil', String(until));
      this.startLockoutCountdown(5 * 60);
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
        sessionStorage.removeItem('userFailedAttempts');
        sessionStorage.removeItem('userLockoutUntil');
        this.errorMessage = '';
      }
    }, 1000);
  }

  // ===== UI HELPERS =====
  get attemptsBarWidth(): number {
    return Math.min((this.failedAttempts / 5) * 100, 100);
  }

  get attemptsBarColor(): string {
    if (this.failedAttempts >= 5) return '#ef4444';
    if (this.failedAttempts >= 3) return '#f59e0b';
    return '#22c55e';
  }

  get passwordStrengthLabel(): string {
    const labels = ['Very Weak', 'Weak', 'Fair', 'Good', 'Strong', 'Very Strong'];
    return labels[this.passwordStrength] || 'Enter password';
  }

  get passwordStrengthColor(): string {
    const colors = ['#ef4444', '#f97316', '#eab308', '#84cc16', '#22c55e', '#16a34a'];
    return colors[this.passwordStrength] || '#6b7280';
  }
}
