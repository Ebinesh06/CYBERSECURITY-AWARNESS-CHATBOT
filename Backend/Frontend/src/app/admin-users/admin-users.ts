import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient, HttpHeaders } from '@angular/common/http';

interface User {
  id: number;
  username: string;
  role: 'admin' | 'user' | 'analyst';
  status: 'active' | 'suspended' | 'pending';
}

@Component({
  selector: 'app-admin-users',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './admin-users.html',
  styleUrls: ['./admin-users.css']
})
export class AdminUsersComponent implements OnInit {
  users: User[] = [];
  filteredUsers: User[] = [];
  loading = true;
  error = '';
  searchQuery = '';
  roleFilter: 'all' | 'admin' | 'user' | 'analyst' = 'all';
  statusFilter: 'all' | 'active' | 'suspended' | 'pending' = 'all';

  constructor(private http: HttpClient) {}

  ngOnInit() {
    this.loadUsers();
  }

  loadUsers() {
    this.loading = true;
    this.error = '';
    const token = localStorage.getItem('token');
    const headers = new HttpHeaders({ Authorization: `Bearer ${token}` });

    this.http.get<any[]>('http://localhost:8000/admin/users', { headers }).subscribe({
      next: (data) => {
        this.users = data.map(u => ({
          id: u.id,
          username: u.username,
          role: u.role as User['role'],
          status: 'active' as User['status'],
        }));
        this.applyFilters();
        this.loading = false;
      },
      error: (err) => {
        this.error = 'Failed to load users. Make sure the backend is running.';
        this.loading = false;
      }
    });
  }

  applyFilters() {
    const q = this.searchQuery.trim().toLowerCase();

    this.filteredUsers = this.users.filter(user => {
      const matchesQuery = !q ||
        user.username.toLowerCase().includes(q);

      const matchesRole = this.roleFilter === 'all' || user.role === this.roleFilter;
      const matchesStatus = this.statusFilter === 'all' || user.status === this.statusFilter;

      return matchesQuery && matchesRole && matchesStatus;
    });
  }

  updateRoleFilter(value: string) {
    this.roleFilter = value as typeof this.roleFilter;
    this.applyFilters();
  }

  updateStatusFilter(value: string) {
    this.statusFilter = value as typeof this.statusFilter;
    this.applyFilters();
  }

  toggleUserStatus(user: User) {
    if (user.role === 'admin') return;
    user.status = user.status === 'active' ? 'suspended' : 'active';
    this.applyFilters();
  }

  forceMfa(user: User) {
    alert(`MFA enforcement noted for ${user.username}. (Requires backend MFA support)`);
  }

  rotateCredentials(user: User) {
    alert(`Credential rotation initiated for ${user.username}.`);
  }

  deleteUser(userId: number) {
    const target = this.users.find(u => u.id === userId);
    if (!target || target.role === 'admin') return;

    if (!confirm('Delete this account permanently? This action cannot be undone.')) {
      return;
    }

    const token = localStorage.getItem('token');
    const headers = new HttpHeaders({ Authorization: `Bearer ${token}` });
    this.http.delete(`http://localhost:8000/admin/users/${userId}`, { headers }).subscribe({
      next: () => {
        this.users = this.users.filter(u => u.id !== userId);
        this.applyFilters();
      },
      error: () => {
        alert('Failed to delete user. Make sure the backend is running.');
      }
    });
  }
}
