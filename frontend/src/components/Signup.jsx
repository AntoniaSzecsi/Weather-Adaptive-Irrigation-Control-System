import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { signup as apiSignup, signupSchema } from '../api/auth';

const Signup = ({ onSwitchToLogin }) => {
    const [formData, setFormData] = useState({
        username: '',
        email: '',
        password: '',
    });
    const [errors, setErrors] = useState({});

    const mutation = useMutation({
        mutationFn: () => apiSignup(formData),
        onSuccess: () => {
            onSwitchToLogin();
        },
        onError: (error) => {
            let errorMessage = 'Signup failed';
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
            signupSchema.parse(formData);
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
            <h2>Sign Up</h2>
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
                    <label>Email</label>
                    <input
                        type="email"
                        value={formData.email}
                        onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    />
                    {errors.email && <span className="error">{errors.email}</span>}
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
                    {mutation.isPending ? 'Signing up...' : 'Sign Up'}
                </button>
            </form>

            <p>
                Already have an account?{' '}
                <button type="button" onClick={onSwitchToLogin} className="link-button">
                    Login
                </button>
            </p>
        </div>
    );
};

export default Signup;

