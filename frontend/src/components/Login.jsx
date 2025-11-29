import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { login as apiLogin, loginSchema, getCurrentUser } from '../api/auth';
import { useAuth } from '../contexts/AuthContext';

const Login = ({ onSwitchToSignup }) => {
    const [formData, setFormData] = useState({ username: '', password: '' });
    const [errors, setErrors] = useState({});
    const { login } = useAuth();
    const navigate = useNavigate();

    const mutation = useMutation({
        mutationFn: () => apiLogin(formData.username, formData.password),
        onSuccess: async (data) => {
            const userData = await getCurrentUser();
            login(userData);
            navigate('/dashboard');
        },
        onError: (error) => {
            let errorMessage = 'Login failed';
            if (error.response) {
                const data = error.response.data;
                if (data.detail) {
                    if (typeof data.detail === 'string') {
                        errorMessage = data.detail;
                    } else if (Array.isArray(data.detail)) {
                        errorMessage = data.detail.map(d => d.msg || JSON.stringify(d)).join(', ');
                    } else {
                        errorMessage = JSON.stringify(data.detail);
                    }
                } else if (data.message) {
                    errorMessage = data.message;
                }
            } else if (error.message) {
                errorMessage = error.message;
            }
            setErrors({ general: errorMessage });
        },
    });

    const handleSubmit = (e) => {
        e.preventDefault();
        setErrors({});

        try {
            loginSchema.parse(formData);
            mutation.mutate();
        } catch (error) {
            if (error.errors) {
                const zodErrors = {};
                error.errors.forEach((err) => {
                    zodErrors[err.path[0]] = err.message;
                });
                setErrors(zodErrors);
            }
        }
    };

    return (
        <div className="auth-container">
            <h2>Login</h2>
            <form onSubmit={handleSubmit}>
                {errors.general && (
                    <div className="error" style={{ marginBottom: '20px' }}>
                        <strong>Error:</strong> {errors.general}
                    </div>
                )}

                <div className="form-group">
                    <label>Username</label>
                    <input
                        type="text"
                        value={formData.username}
                        onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                    />
                    {errors.username && <span className="error">{errors.username}</span>}
                </div>

                <div className="form-group">
                    <label>Password</label>
                    <input
                        type="password"
                        value={formData.password}
                        onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                    />
                    {errors.password && <span className="error">{errors.password}</span>}
                </div>

                <button type="submit" disabled={mutation.isPending}>
                    {mutation.isPending ? 'Logging in...' : 'Login'}
                </button>
            </form>

            <p>
                Don't have an account?{' '}
                <button type="button" onClick={onSwitchToSignup} className="link-button">
                    Sign up
                </button>
            </p>
        </div>
    );
};

export default Login;

