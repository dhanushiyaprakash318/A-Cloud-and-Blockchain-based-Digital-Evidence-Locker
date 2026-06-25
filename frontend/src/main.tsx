import { createRoot } from "react-dom/client";
import App from "./App.tsx";
import "./index.css";

// Initialize theme from localStorage, else system preference
if (typeof document !== 'undefined') {
	try {
		const stored = localStorage.getItem('theme');
		if (stored === 'dark') {
			document.documentElement.classList.add('dark');
		} else if (stored === 'light') {
			document.documentElement.classList.remove('dark');
		} else if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
			document.documentElement.classList.add('dark');
		} else {
			document.documentElement.classList.remove('dark');
		}
	} catch {
		// ignore storage access errors
	}
}

createRoot(document.getElementById("root")!).render(<App />);
