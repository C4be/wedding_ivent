document.addEventListener('DOMContentLoaded', function() {
    // Initialize AOS
    AOS.init({
        duration: 800,
        easing: 'ease-out-cubic',
        once: true,
        offset: 50
    });

    // ============ Theme Toggle ============
    const themeToggle = document.getElementById('themeToggle');
    const savedTheme = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', savedTheme);

    themeToggle.addEventListener('click', () => {
        const currentTheme = document.documentElement.getAttribute('data-theme');
        const newTheme = currentTheme === 'light' ? 'dark' : 'light';
        document.documentElement.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);
    });

    // ============ Countdown Timer ============
    const eventDate = new Date(CONFIG.eventDate).getTime();

    function updateCountdown() {
        const now = new Date().getTime();
        const distance = eventDate - now;

        if (distance > 0) {
            const days = Math.floor(distance / (1000 * 60 * 60 * 24));
            const hours = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
            const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
            const seconds = Math.floor((distance % (1000 * 60)) / 1000);

            document.getElementById('days').textContent = String(days).padStart(2, '0');
            document.getElementById('hours').textContent = String(hours).padStart(2, '0');
            document.getElementById('minutes').textContent = String(minutes).padStart(2, '0');
            document.getElementById('seconds').textContent = String(seconds).padStart(2, '0');
        } else {
            document.getElementById('countdown').innerHTML = '<p style="font-size: 1.5rem;">🎉 Сегодня наш день!</p>';
        }
    }

    updateCountdown();
    setInterval(updateCountdown, 1000);

    // ============ Navigation ============
    const nav = document.getElementById('nav');
    const navToggle = document.getElementById('navToggle');
    const navMenu = document.getElementById('navMenu');

    // Scroll effect
    window.addEventListener('scroll', () => {
        if (window.scrollY > 100) {
            nav.classList.add('scrolled');
        } else {
            nav.classList.remove('scrolled');
        }
    });

    // Mobile menu toggle
    navToggle.addEventListener('click', () => {
        navToggle.classList.toggle('active');
        navMenu.classList.toggle('active');
    });

    // Close menu on link click
    navMenu.querySelectorAll('a').forEach(link => {
        link.addEventListener('click', () => {
            navToggle.classList.remove('active');
            navMenu.classList.remove('active');
        });
    });

    // ============ FAQ Accordion ============
    document.querySelectorAll('.faq-question').forEach(button => {
        button.addEventListener('click', () => {
            const item = button.parentElement;
            const wasActive = item.classList.contains('active');
            
            // Close all
            document.querySelectorAll('.faq-item').forEach(i => i.classList.remove('active'));
            
            // Open clicked if wasn't active
            if (!wasActive) {
                item.classList.add('active');
            }
        });
    });

    // ============ RSVP Form ============
    const rsvpForm = document.getElementById('rsvpForm');
    const conditionalFields = document.getElementById('conditionalFields');
    const attendingRadios = document.querySelectorAll('input[name="attending"]');

    attendingRadios.forEach(radio => {
        radio.addEventListener('change', (e) => {
            if (e.target.value === 'yes') {
                conditionalFields.classList.add('show');
            } else {
                conditionalFields.classList.remove('show');
            }
        });
    });

    rsvpForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const formData = new FormData(rsvpForm);
        const data = {
            first_name: formData.get('first_name'),
            last_name: formData.get('last_name'),
            contact: formData.get('contact'),
            attending: formData.get('attending') === 'yes',
            guests_count: formData.get('guests_count') || 1,
            children: formData.get('children') || '',
            food_preferences: formData.get('food_preferences') || ''
        };

        try {
            const response = await fetch('/api/rsvp', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });

            const result = await response.json();
            
            if (result.status === 'success') {
                showToast('Спасибо! Ваш ответ отправлен 💕', 'success');
                rsvpForm.reset();
                conditionalFields.classList.remove('show');
            } else {
                showToast('Ошибка при отправке. Попробуйте позже.', 'error');
            }
        } catch (error) {
            showToast('Ошибка сети. Проверьте подключение.', 'error');
        }
    });

    // ============ Question Form ============
    const questionForm = document.getElementById('questionForm');

    questionForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const formData = new FormData(questionForm);
        const data = {
            name: formData.get('name') || 'Аноним',
            contact: formData.get('contact') || '',
            question: formData.get('question')
        };

        try {
            const response = await fetch('/api/question', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });

            const result = await response.json();
            
            if (result.status === 'success') {
                showToast('Вопрос отправлен! Мы скоро ответим.', 'success');
                questionForm.reset();
            } else {
                showToast('Ошибка при отправке.', 'error');
            }
        } catch (error) {
            showToast('Ошибка сети.', 'error');
        }
    });

    // ============ Toast Notification ============
    function showToast(message, type = 'success') {
        const toast = document.getElementById('toast');
        const toastMessage = toast.querySelector('.toast-message');
        
        toastMessage.textContent = message;
        toast.className = `toast ${type} show`;
        
        setTimeout(() => {
            toast.classList.remove('show');
        }, 4000);
    }

    // ============ Smooth Scroll for anchor links ============
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                const offset = 80;
                const targetPosition = target.getBoundingClientRect().top + window.pageYOffset - offset;
                window.scrollTo({
                    top: targetPosition,
                    behavior: 'smooth'
                });
            }
        });
    });

    // ============ Load Gallery (if exists) ============
    async function loadGallery() {
        try {
            const response = await fetch('/api/gallery');
            const images = await response.json();
            
            if (images.length > 0) {
                const gallerySection = document.getElementById('gallery');
                const galleryGrid = document.getElementById('galleryGrid');
                
                gallerySection.style.display = 'block';
                
                images.forEach(img => {
                    const item = document.createElement('div');
                    item.className = 'gallery-item';
                    item.setAttribute('data-aos', 'fade-up');
                    item.innerHTML = `
                        <img src="${img.url}" alt="${img.caption || 'Wedding photo'}">
                    `;
                    galleryGrid.appendChild(item);
                });
            }
        } catch (error) {
            console.log('Gallery not loaded');
        }
    }

    loadGallery();
});
