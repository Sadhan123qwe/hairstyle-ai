/**
 * HairStyle AI - Main JavaScript
 * Author: S.Thiruselvam | Roll: 23COS263
 */

// =============================================
//  Navbar & Navigation
// =============================================
const navbar = document.getElementById('navbar');
const navToggle = document.getElementById('navToggle');
const navLinks = document.getElementById('navLinks');

// Sticky navbar with scroll effect + classic gold glow class
window.addEventListener('scroll', () => {
    if (window.scrollY > 20) {
        navbar.style.boxShadow = '0 4px 30px rgba(0,0,0,0.5)';
        navbar.style.background = 'rgba(15, 15, 26, 0.97)';
        navbar.classList.add('scrolled');
    } else {
        navbar.style.boxShadow = 'none';
        navbar.style.background = 'rgba(15, 15, 26, 0.85)';
        navbar.classList.remove('scrolled');
    }
});

// Mobile nav toggle
if (navToggle) {
    navToggle.addEventListener('click', () => {
        navLinks.classList.toggle('open');
        const spans = navToggle.querySelectorAll('span');
        const isOpen = navLinks.classList.contains('open');
        spans[0].style.transform = isOpen ? 'rotate(45deg) translate(5px, 5px)' : '';
        spans[1].style.opacity = isOpen ? '0' : '1';
        spans[2].style.transform = isOpen ? 'rotate(-45deg) translate(5px, -5px)' : '';
    });
}

// Close nav when clicking outside or on a link
document.addEventListener('click', (e) => {
    if (navLinks && !navLinks.contains(e.target) && !navToggle.contains(e.target)) {
        navLinks.classList.remove('open');
    }
});

// =============================================
//  Flash Messages Auto-dismiss
// =============================================
function setupFlashMessages() {
    const flashes = document.querySelectorAll('.flash-message');
    flashes.forEach((flash, index) => {
        setTimeout(() => {
            flash.style.animation = 'slideIn 0.3s ease reverse';
            setTimeout(() => flash.remove(), 300);
        }, 5000 + (index * 500));
    });
}

setupFlashMessages();

// =============================================
//  Password Toggle
// =============================================
function togglePassword(inputId) {
    const input = document.getElementById(inputId);
    const icon = document.getElementById(inputId + '-eye');
    if (!input || !icon) return;

    if (input.type === 'password') {
        input.type = 'text';
        icon.classList.replace('fa-eye', 'fa-eye-slash');
    } else {
        input.type = 'password';
        icon.classList.replace('fa-eye-slash', 'fa-eye');
    }
}

// =============================================
//  Intersection Observer for Scroll Animations
// =============================================
const animateEls = document.querySelectorAll(
    '.step-card, .shape-card, .feature-card, .dash-stat-card, .history-card, .tech-item, .about-stat'
);

if (animateEls.length > 0) {
    const observer = new IntersectionObserver((entries) => {
        entries.forEach((entry, index) => {
            if (entry.isIntersecting) {
                entry.target.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
                entry.target.style.transitionDelay = `${(index % 4) * 0.08}s`;
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.1, rootMargin: '0px 0px -40px 0px' });

    animateEls.forEach((el) => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(24px)';
        observer.observe(el);
    });
}

// =============================================
//  Smooth Scroll for Anchor Links
// =============================================
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            e.preventDefault();
            target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    });
});
