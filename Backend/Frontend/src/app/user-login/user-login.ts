import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { HttpClient } from '@angular/common/http';

@Component({
  selector: 'app-user-login',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './user-login.html',
  styleUrls: ['./user-login.css']
})
export class UserLoginComponent {
  username = '';
  password = '';
  isLoading = false;
  errorMessage = '';
  isSignUp = false;

  constructor(
    private router: Router,
    private http: HttpClient
  ) {}

  toggleSignUp() {
    this.isSignUp = !this.isSignUp;
    this.username = '';
    this.password = '';
    this.errorMessage = '';
  }

  login() {
    if (!this.username.trim() || !this.password.trim()) {
      this.errorMessage = 'Please enter both username and password';
      return;
    }

    this.isLoading = true;
    this.errorMessage = '';

    this.http.post('http://127.0.0.1:8000/auth/login', {
      username: this.username.trim(),
      password: this.password.trim()
    }).subscribe({
      next: (res: any) => {
        localStorage.setItem('token', res.access_token);
        localStorage.setItem('role', res.role);
        localStorage.setItem('username', res.username || this.username);
        console.log("User authenticated. Entering Chat...");
        this.router.navigate(['/chat']);
        this.isLoading = false;
      },
      error: (error) => {
        this.isLoading = false;
        this.errorMessage = "Invalid username or password";
        console.error('Login error:', error);
      }
    });
  }

  signUp() {
    if (!this.username.trim() || !this.password.trim()) {
      this.errorMessage = 'Please enter username and password';
      return;
    }

    this.isLoading = true;
    this.errorMessage = '';

    this.http.post('http://127.0.0.1:8000/auth/signup', {
      username: this.username.trim(),
      password: this.password.trim()
    }).subscribe({
      next: (res: any) => {
        localStorage.setItem('token', res.access_token);
        localStorage.setItem('role', res.role);
        localStorage.setItem('username', res.username || this.username);
        this.router.navigate(['/chat']);
        this.isLoading = false;
      },
      error: (error: any) => {
        this.isLoading = false;
        this.errorMessage = error.error?.detail || "Failed to create account";
      }
    });
  }
}
