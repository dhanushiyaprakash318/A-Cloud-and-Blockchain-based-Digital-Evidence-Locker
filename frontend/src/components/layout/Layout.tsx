import React from 'react';
import { Navbar } from './Navbar';
import { Footer } from './Footer';
import Particles from '../ui/Particles';
import '../ui/Particles.css';
import ClickSpark from '../ClickSpark';


interface LayoutProps {
  children: React.ReactNode;
}

export const Layout: React.FC<LayoutProps> = ({ children }) => {
  return (
    <div className="min-h-screen flex flex-col bg-background" style={{ position: 'relative', overflow: 'hidden' }}>
      <div style={{ position: 'fixed', width: '100vw', height: '100vh', top: 0, left: 0, zIndex: 0 }}>
        <Particles
          particleColors={['#ffffff', '#ffffff']}
          particleCount={200}
          particleSpread={10}
          speed={0.1}
          particleBaseSize={100}
          moveParticlesOnHover={true}
          alphaParticles={false}
          disableRotation={false}
        />
      </div>
      <div style={{ position: 'relative', zIndex: 1, minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
        <Navbar />
        <main className="flex-1">
          <ClickSpark>
            {children}
          </ClickSpark>
        </main>
        <Footer />
      </div>
    </div>
  );
};