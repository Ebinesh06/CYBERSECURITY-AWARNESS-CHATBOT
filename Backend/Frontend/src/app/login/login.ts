import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { HttpClient } from '@angular/common/http';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './login.html',
  styleUrls: ['./login.css']
})
export class LoginComponent {
  username = '';
  password = '';
  isLoading = false;
  errorMessage = '';

  constructor(
    private router: Router,
    private http: HttpClient
  ) {}

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
        // 1. Save the keys to the vault
        localStorage.setItem('token', res.access_token);
        localStorage.setItem('role', res.role);

        // 2. Traffic Control: Send them to the right "Interface"
        if (res.role === 'admin') {
          console.log("Admin detected. Entering Dashboard...");
          this.router.navigate(['/admin-dashboard']);
        } else {
          console.log("User detected. Entering Chat...");
          this.router.navigate(['/chat']);
        }
        this.isLoading = false;
      },
      error: (error) => {
        this.isLoading = false;
        this.errorMessage = "Access Denied. Please check your credentials.";
        console.error('Login error:', error);
      }
    });
  }
}
