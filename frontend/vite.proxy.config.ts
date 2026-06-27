import { ProxyOptions } from 'vite';

const proxy: Record<string, string | ProxyOptions> = {
  '/api': {
    target: 'http://localhost:8000',
    changeOrigin: true,
    secure: false,
  },
};

export default proxy;
