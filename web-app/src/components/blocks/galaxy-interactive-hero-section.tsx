"use client";

import React, { useEffect, useRef, useState } from 'react';
import { ChevronDown, Menu, X, PlayCircle, Sparkles, ArrowRight, ShieldCheck, Zap } from 'lucide-react';
import { motion } from 'framer-motion';
import { InteractiveCursor } from './interactive-cursor';

function StarfieldCanvas() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationFrameId: number;
    let width = (canvas.width = window.innerWidth);
    let height = (canvas.height = window.innerHeight);
    let nebulaGradient: CanvasGradient | null = null;

    const createGradient = () => {
      nebulaGradient = ctx.createRadialGradient(
        width * 0.5,
        height * 0.4,
        50,
        width * 0.5,
        height * 0.5,
        Math.max(width, height) * 0.7
      );
      nebulaGradient.addColorStop(0, 'rgba(99, 102, 241, 0.12)');
      nebulaGradient.addColorStop(0.5, 'rgba(6, 182, 212, 0.05)');
      nebulaGradient.addColorStop(1, 'rgba(0, 0, 0, 0)');
    };
    
    createGradient();

    const handleResize = () => {
      if (!canvas) return;
      width = canvas.width = window.innerWidth;
      height = canvas.height = window.innerHeight;
      createGradient();
    };
    window.addEventListener('resize', handleResize, { passive: true });

    // Generate stars
    const starCount = Math.min(180, Math.floor((width * height) / 8000));
    const stars = Array.from({ length: starCount }, () => ({
      x: Math.random() * width,
      y: Math.random() * height,
      radius: Math.random() * 1.5 + 0.5,
      alpha: Math.random() * 0.8 + 0.2,
      velocity: Math.random() * 0.3 + 0.1,
      twinkle: Math.random() * 0.02 + 0.005,
    }));

    const render = () => {
      ctx.clearRect(0, 0, width, height);

      // Deep galactic nebula glow
      if (nebulaGradient) {
        ctx.fillStyle = nebulaGradient;
        ctx.fillRect(0, 0, width, height);
      }

      // Draw stars
      stars.forEach((star) => {
        star.y -= star.velocity;
        if (star.y < 0) {
          star.y = height;
          star.x = Math.random() * width;
        }

        star.alpha += star.twinkle;
        if (star.alpha > 0.9 || star.alpha < 0.2) {
          star.twinkle = -star.twinkle;
        }

        ctx.beginPath();
        ctx.arc(star.x, star.y, star.radius, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(255, 255, 255, ${Math.max(0.1, Math.min(1, star.alpha))})`;
        ctx.shadowBlur = 4;
        ctx.shadowColor = '#6366f1';
        ctx.fill();
      });

      animationFrameId = requestAnimationFrame(render);
    };

    render();

    return () => {
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener('resize', handleResize);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="absolute inset-0 w-full h-full pointer-events-none z-0"
      style={{ opacity: 0.9 }}
    />
  );
}

function HeroSplineBackground() {
  const containerRef = useRef<HTMLDivElement>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    // Check if script already exists to avoid redundant downloads
    const existing = document.querySelector('script[src*="spline-viewer.js"]');
    if (existing) {
      setTimeout(() => setLoaded(true), 0);
      return;
    }

    const script = document.createElement('script');
    script.type = 'module';
    script.src = 'https://unpkg.com/@splinetool/viewer@1.9.82/build/spline-viewer.js';
    script.async = true;
    script.onload = () => setLoaded(true);
    script.onerror = () => {
      console.warn("Spline viewer script load failed, falling back to starfield canvas.");
    };
    document.head.appendChild(script);

    return () => {
      if (document.head.contains(script)) {
        try {
          document.head.removeChild(script);
        } catch {
          // Ignore if already removed
        }
      }
    };
  }, []);

  useEffect(() => {
    const container = containerRef.current;
    if (loaded && container) {
      container.innerHTML = '';
      try {
        const viewer = document.createElement('spline-viewer');
        viewer.setAttribute('url', 'https://prod.spline.design/us3ALejTXl6usHZ7/scene.splinecode');
        viewer.style.width = '100%';
        viewer.style.height = '100vh';
        container.appendChild(viewer);
      } catch (err) {
        console.warn("Could not mount spline-viewer:", err);
      }

      return () => {
        if (container) {
          container.innerHTML = '';
        }
      };
    }
  }, [loaded]);

  return (
    <div
      style={{
        position: 'relative',
        width: '100%',
        height: '100vh',
        pointerEvents: 'auto',
        overflow: 'hidden',
      }}
    >
      <StarfieldCanvas />
      <div ref={containerRef} style={{ width: '100%', height: '100vh', position: 'relative', zIndex: 1 }} />
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100%',
          height: '100vh',
          background: `
            linear-gradient(to right, rgba(0, 0, 0, 0.85), transparent 35%, transparent 65%, rgba(0, 0, 0, 0.85)),
            linear-gradient(to bottom, transparent 40%, rgba(0, 0, 0, 0.95))
          `,
          pointerEvents: 'none',
          zIndex: 2,
        }}
      />
    </div>
  );
}

function ScreenshotSection({ screenshotRef }: { screenshotRef: React.RefObject<HTMLDivElement | null> }) {
  return (
    <section className="relative z-10 container mx-auto px-4 md:px-6 lg:px-8 mt-11 md:mt-12">
      <div
        ref={screenshotRef}
        className="bg-gray-900 rounded-xl overflow-hidden shadow-2xl border border-gray-700/50 w-full md:w-[85%] lg:w-[75%] mx-auto transition-transform duration-100 ease-out"
      >
        <div className="bg-gray-800/80 px-4 py-3 border-b border-gray-700/50 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <span className="w-3 h-3 rounded-full bg-red-500/80 inline-block"></span>
            <span className="w-3 h-3 rounded-full bg-yellow-500/80 inline-block"></span>
            <span className="w-3 h-3 rounded-full bg-green-500/80 inline-block"></span>
            <span className="text-xs text-gray-400 ml-2 font-mono">http://localhost:8000/</span>
          </div>
          <span className="text-xs text-indigo-400 font-semibold flex items-center gap-1">
            <ShieldCheck className="w-3.5 h-3.5" /> Legal Metrology MRP Enforced
          </span>
        </div>
        <div className="relative aspect-[16/9] w-full bg-slate-950 flex items-center justify-center overflow-hidden">
          <img
            src="https://images.unsplash.com/photo-1551288049-bebda4e38f71?auto=format&fit=crop&w=1600&q=80"
            alt="AI Pricing Engine Analytics Dashboard"
            loading="lazy"
            decoding="async"
            className="w-full h-full object-cover block"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent flex flex-col justify-end p-6">
            <h3 className="text-xl md:text-2xl font-bold text-white mb-2">Live Retail Pricing Command Center</h3>
            <p className="text-sm text-gray-300 max-w-xl">
              Real-time LightGBM demand simulation, price elasticity curves, and automated inventory clearance balancing.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}

function HeroContent() {
  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.2,
        delayChildren: 0.3,
      },
    },
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 30 },
    visible: { opacity: 1, y: 0, transition: { duration: 0.8, ease: "easeOut" } },
  };

  return (
    <motion.div 
      className="text-left text-white pt-16 sm:pt-24 md:pt-32 px-4 max-w-3xl"
      variants={containerVariants}
      initial="hidden"
      animate="visible"
    >
      <motion.div variants={itemVariants} className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/20 border border-indigo-500/40 text-indigo-300 text-xs font-semibold uppercase tracking-wider mb-6">
        <Zap className="w-3.5 h-3.5 text-cyan-400" /> Enterprise Pricing AI &bull; India Retail Edition
      </motion.div>
      <motion.h1 variants={itemVariants} className="text-3xl sm:text-5xl md:text-7xl font-bold mb-4 leading-tight tracking-wide">
        Elevate your <br className="sm:hidden" />retail strategy<br className="sm:hidden" /> to an art form.
      </motion.h1>
      <motion.p variants={itemVariants} className="text-base sm:text-lg md:text-xl mb-6 sm:mb-8 opacity-80 max-w-xl">
        Manage all of your pricing and inventory decisions — sales velocity, competitor signals, margin optimization, and successor launches — on a single high-performance engine powered by AI.
      </motion.p>
      <motion.div variants={itemVariants} className="flex pointer-events-auto flex-col sm:flex-row items-start space-y-3 sm:space-y-0 sm:space-x-3">
        <a
          href="http://localhost:8000"
          className="bg-indigo-600 hover:bg-indigo-500 text-white font-semibold py-2.5 sm:py-3 px-6 sm:px-8 rounded-full transition duration-300 w-full sm:w-auto flex items-center justify-center gap-2 shadow-lg shadow-indigo-600/30"
        >
          Open AI Dashboard <ArrowRight className="w-4 h-4" />
        </a>
        <button
          onClick={() => {
            const el = document.getElementById('features-section');
            if (el) el.scrollIntoView({ behavior: 'smooth' });
          }}
          className="pointer-events-auto bg-black/60 border border-gray-600 hover:border-gray-400 text-gray-200 hover:text-white font-medium py-2.5 sm:py-3 px-6 sm:px-8 rounded-full transition duration-300 flex items-center justify-center w-full sm:w-auto"
        >
          <PlayCircle className="w-4 h-4 sm:w-5 sm:h-5 mr-2" />
          Explore Architecture
        </button>
      </motion.div>
    </motion.div>
  );
}

function Navbar() {
  const [hoveredNavItem, setHoveredNavItem] = useState<string | null>(null);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [mobileDropdowns, setMobileDropdowns] = useState({
    features: false,
    enterprise: false,
    resources: false,
  });

  const handleMouseEnterNavItem = (item: string) => setHoveredNavItem(item);
  const handleMouseLeaveNavItem = () => setHoveredNavItem(null);

  const toggleMobileMenu = () => {
    setIsMobileMenuOpen(!isMobileMenuOpen);
    if (isMobileMenuOpen) {
      setMobileDropdowns({ features: false, enterprise: false, resources: false });
    }
  };

  const toggleMobileDropdown = (key: keyof typeof mobileDropdowns) => {
    setMobileDropdowns((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const navLinkClass = (itemName: string, extraClasses = '') => {
    const isCurrentItemHovered = hoveredNavItem === itemName;
    const isAnotherItemHovered = hoveredNavItem !== null && !isCurrentItemHovered;

    const colorClass = isCurrentItemHovered
      ? 'text-white'
      : isAnotherItemHovered
      ? 'text-gray-500'
      : 'text-gray-300';

    return `text-sm transition duration-150 ${colorClass} ${extraClasses}`;
  };

  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth >= 1024 && isMobileMenuOpen) {
        setIsMobileMenuOpen(false);
        setMobileDropdowns({ features: false, enterprise: false, resources: false });
      }
    };
    window.addEventListener('resize', handleResize, { passive: true });
    return () => window.removeEventListener('resize', handleResize);
  }, [isMobileMenuOpen]);

  return (
    <nav
      className="fixed top-0 left-0 right-0 z-30"
      style={{
        backgroundColor: 'rgba(10, 15, 29, 0.75)',
        backdropFilter: 'blur(12px)',
        WebkitBackdropFilter: 'blur(12px)',
        borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
      }}
    >
      <div className="container mx-auto px-4 py-4 md:px-6 lg:px-8 flex items-center justify-between">
        <div className="flex items-center space-x-6 lg:space-x-8">
          <div className="text-white flex items-center space-x-2">
            <Sparkles className="w-7 h-7 text-indigo-400" />
            <span className="font-bold text-lg hidden md:block tracking-tight">ApexPricing AI</span>
          </div>

          <div className="hidden lg:flex items-center space-x-6">
            <div
              className="relative group"
              onMouseEnter={() => handleMouseEnterNavItem('features')}
              onMouseLeave={handleMouseLeaveNavItem}
            >
              <a href="#features" className={navLinkClass('features', 'flex items-center')}>
                Features
                <ChevronDown className="ml-1 w-3 h-3 group-hover:rotate-180 transition-transform duration-200" />
              </a>
              <div
                className="absolute left-0 mt-2 w-52 bg-slate-900/90 rounded-md shadow-xl py-2 border border-gray-700/50 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-30"
                style={{ backdropFilter: 'blur(12px)' }}
              >
                <a href="#features" className="block px-4 py-2 text-sm text-gray-300 hover:text-white hover:bg-slate-800 transition">
                  Demand Forecasting (LightGBM)
                </a>
                <a href="#features" className="block px-4 py-2 text-sm text-gray-300 hover:text-white hover:bg-slate-800 transition">
                  Price Elasticity Modeling
                </a>
                <a href="#features" className="block px-4 py-2 text-sm text-gray-300 hover:text-white hover:bg-slate-800 transition">
                  Inventory Lifecycle Optimizer
                </a>
              </div>
            </div>

            <a
              href="http://localhost:8000"
              className={navLinkClass('dashboard')}
              onMouseEnter={() => handleMouseEnterNavItem('dashboard')}
              onMouseLeave={handleMouseLeaveNavItem}
            >
              Live Dashboard
            </a>

            <a
              href="#pricing"
              className={navLinkClass('pricing')}
              onMouseEnter={() => handleMouseEnterNavItem('pricing')}
              onMouseLeave={handleMouseLeaveNavItem}
            >
              Indian Market Specs
            </a>
          </div>
        </div>

        <div className="flex items-center space-x-4 md:space-x-6">
          <a
            href="http://localhost:8000"
            className="bg-indigo-600 hover:bg-indigo-500 text-white font-semibold py-2 px-5 rounded-full text-sm md:text-base transition duration-200 shadow-md shadow-indigo-600/30"
          >
            Open Dashboard
          </a>
          <button className="lg:hidden text-white p-2" onClick={toggleMobileMenu} aria-label="Toggle mobile menu">
            {isMobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </div>
      </div>

      <div
        className={`lg:hidden bg-slate-950/95 border-t border-gray-800 absolute top-full left-0 right-0 z-30 overflow-hidden transition-all duration-300 ease-in-out ${
          isMobileMenuOpen ? 'max-h-screen opacity-100 pointer-events-auto' : 'max-h-0 opacity-0 pointer-events-none'
        }`}
        style={{ backdropFilter: 'blur(12px)' }}
      >
        <div className="px-4 py-6 flex flex-col space-y-4">
          <a href="http://localhost:8000" className="text-indigo-400 font-semibold text-sm py-2">
            Launch AI Pricing Dashboard &rarr;
          </a>
          <a href="#features" className="text-gray-300 hover:text-white text-sm py-2" onClick={toggleMobileMenu}>
            Features & Algorithms
          </a>
        </div>
      </div>
    </nav>
  );
}

export const HeroSection = () => {
  const screenshotRef = useRef<HTMLDivElement>(null);
  const heroContentRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let ticking = false;

    const handleScroll = () => {
      if (!ticking) {
        requestAnimationFrame(() => {
          const scrollPosition = window.scrollY;
          if (screenshotRef.current) {
            screenshotRef.current.style.transform = `translateY(-${scrollPosition * 0.35}px)`;
          }

          const maxScroll = 400;
          const opacity = 1 - Math.min(scrollPosition / maxScroll, 1);
          if (heroContentRef.current) {
            heroContentRef.current.style.opacity = opacity.toString();
          }
          ticking = false;
        });
        ticking = true;
      }
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <div className="relative">
      <InteractiveCursor />
      <Navbar />

      <div className="relative min-h-screen">
        <div className="absolute inset-0 z-0 pointer-events-auto">
          <HeroSplineBackground />
        </div>

        <div
          ref={heroContentRef}
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            width: '100%',
            height: '100vh',
            display: 'flex',
            justifyContent: 'flex-start',
            alignItems: 'center',
            zIndex: 10,
            pointerEvents: 'none',
          }}
        >
          <div className="container mx-auto">
            <HeroContent />
          </div>
        </div>
      </div>

      <div className="bg-black relative z-10" style={{ marginTop: '-10vh' }}>
        <ScreenshotSection screenshotRef={screenshotRef} />
        <div id="features-section" className="container mx-auto px-4 py-20 text-white">
          <h2 className="text-3xl md:text-5xl font-bold text-center mb-6">Engineered for Indian Retail Realities</h2>
          <p className="text-center max-w-2xl mx-auto text-gray-400 text-base md:text-lg mb-12">
            Built from the ground up to address Legal Metrology MRP enforcement, competitor web scrapers, and successor model obsolescence discounts.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-5xl mx-auto">
            <motion.div 
              initial={{ opacity: 0, y: 50 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-100px" }}
              transition={{ duration: 0.6, delay: 0.1 }}
              className="group bg-slate-900/60 border border-slate-800 hover:border-indigo-500/50 rounded-xl p-6 backdrop-blur-md transition-all duration-300 hover:shadow-[0_0_30px_rgba(99,102,241,0.15)] relative overflow-hidden"
            >
              <div className="absolute inset-0 bg-gradient-to-br from-indigo-500/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
              <div className="w-10 h-10 rounded-lg bg-indigo-500/20 text-indigo-400 flex items-center justify-center mb-4 relative z-10 group-hover:scale-110 transition-transform duration-300">
                <Sparkles className="w-5 h-5" />
              </div>
              <h3 className="text-lg font-bold mb-2 relative z-10">Demand Forecaster</h3>
              <p className="text-sm text-gray-400 relative z-10 group-hover:text-gray-300 transition-colors">
                Trained LightGBM model evaluating price elasticity, festive seasonality, and competitor availability with monotonic constraints.
              </p>
            </motion.div>

            <motion.div 
              initial={{ opacity: 0, y: 50 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-100px" }}
              transition={{ duration: 0.6, delay: 0.2 }}
              className="group bg-slate-900/60 border border-slate-800 hover:border-cyan-500/50 rounded-xl p-6 backdrop-blur-md transition-all duration-300 hover:shadow-[0_0_30px_rgba(6,182,212,0.15)] relative overflow-hidden"
            >
              <div className="absolute inset-0 bg-gradient-to-br from-cyan-500/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
              <div className="w-10 h-10 rounded-lg bg-cyan-500/20 text-cyan-400 flex items-center justify-center mb-4 relative z-10 group-hover:scale-110 transition-transform duration-300">
                <Zap className="w-5 h-5" />
              </div>
              <h3 className="text-lg font-bold mb-2 relative z-10">Lifecycle Optimizer</h3>
              <p className="text-sm text-gray-400 relative z-10 group-hover:text-gray-300 transition-colors">
                SciPy constrained solver maximizing net profit while factoring daily inventory carrying costs and post-launch write-downs.
              </p>
            </motion.div>

            <motion.div 
              initial={{ opacity: 0, y: 50 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-100px" }}
              transition={{ duration: 0.6, delay: 0.3 }}
              className="group bg-slate-900/60 border border-slate-800 hover:border-emerald-500/50 rounded-xl p-6 backdrop-blur-md transition-all duration-300 hover:shadow-[0_0_30px_rgba(16,185,129,0.15)] relative overflow-hidden"
            >
              <div className="absolute inset-0 bg-gradient-to-br from-emerald-500/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
              <div className="w-10 h-10 rounded-lg bg-emerald-500/20 text-emerald-400 flex items-center justify-center mb-4 relative z-10 group-hover:scale-110 transition-transform duration-300">
                <ShieldCheck className="w-5 h-5" />
              </div>
              <h3 className="text-lg font-bold mb-2 relative z-10">Legal Metrology MRP</h3>
              <p className="text-sm text-gray-400 relative z-10 group-hover:text-gray-300 transition-colors">
                Mathematical hard bound ensuring no recommendation ever exceeds the legally mandated Maximum Retail Price ceiling.
              </p>
            </motion.div>
          </div>
        </div>
      </div>
    </div>
  );
};
