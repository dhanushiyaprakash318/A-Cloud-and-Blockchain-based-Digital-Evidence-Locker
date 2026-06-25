import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useRole } from '@/contexts/RoleContext';
import { auth } from '@/services/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useToast } from '@/hooks/use-toast';

const Login: React.FC = () => {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const { setRole } = useRole();
    const navigate = useNavigate();
    const { toast } = useToast();

    const handleLogin = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            const data = await auth.login(username, password);
            localStorage.setItem('token', data.access_token);

            // Map backend roles to frontend types
            const roleMap: Record<string, 'police' | 'forensics' | 'judge'> = {
                'Polaris': 'police',
                'Forensics': 'forensics',
                'Judge': 'judge'
            };

            const userRole = roleMap[data.role];
            localStorage.setItem('role', userRole);
            setRole(userRole);

            toast({
                title: 'Login Successful',
                description: `Welcome back, ${data.role}`,
            });
            navigate('/');
        } catch (error) {
            toast({
                variant: 'destructive',
                title: 'Login Failed',
                description: 'Invalid username or password',
            });
        }
    };

    return (
        <div className="min-h-screen flex items-center justify-center bg-background p-4">
            <Card className="w-full max-w-md">
                <CardHeader>
                    <CardTitle className="text-2xl text-center">Digital Evidence Locker</CardTitle>
                </CardHeader>
                <CardContent>
                    <form onSubmit={handleLogin} className="space-y-4">
                        <div className="space-y-2">
                            <label>Username</label>
                            <Input
                                value={username}
                                onChange={(e) => setUsername(e.target.value)}
                                placeholder="polaris / forensics / judge"
                            />
                        </div>
                        <div className="space-y-2">
                            <label>Password</label>
                            <Input
                                type="password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                placeholder="password123"
                            />
                        </div>
                        <Button type="submit" className="w-full">
                            Login
                        </Button>
                    </form>
                </CardContent>
            </Card>
        </div>
    );
};

export default Login;
