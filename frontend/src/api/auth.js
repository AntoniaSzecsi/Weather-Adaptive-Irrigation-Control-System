import apiClient from './client';
import { z } from 'zod';

export const signupSchema = z.object({
    username: z.string().min(3, 'Username must be at least 3 characters'),
    email: z.string().email('Invalid email address'),
    password: z.string().min(6, 'Password must be at least 6 characters'),
});

export const loginSchema = z.object({
    username: z.string().min(1, 'Username is required'),
    password: z.string().min(1, 'Password is required'),
});

export const signup = async (data) => {
    const response = await apiClient.post('/signup', data);
    return response.data;
};

export const login = async (username, password) => {
    const params = new URLSearchParams();
    params.append('username', username);
    params.append('password', password);

    const response = await apiClient.post('/token', params.toString(), {
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
    });

    if (response.data.access_token) {
        localStorage.setItem('token', response.data.access_token);
    }

    return response.data;
};

export const getCurrentUser = async () => {
    const response = await apiClient.get('/me');
    return response.data;
};

export const logout = () => {
    localStorage.removeItem('token');
};

