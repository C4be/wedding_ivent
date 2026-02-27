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

    // ============ Timeline Tabs ============
    const timelineTabs = document.querySelectorAll('.timeline-tab');
    const timelineContents = document.querySelectorAll('.timeline-content');

    timelineTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const day = tab.getAttribute('data-day');
            
            // Remove active from all tabs and contents
            timelineTabs.forEach(t => t.classList.remove('active'));
            timelineContents.forEach(c => c.classList.remove('active'));
            
            // Add active to clicked tab and corresponding content
            tab.classList.add('active');
            document.getElementById(`timeline-day-${day}`).classList.add('active');
            
            // Refresh AOS for new content
            AOS.refresh();
        });
    });

    // ============ Story Slider ============
    const sliderTrack = document.getElementById('sliderTrack');
    const sliderPrev = document.getElementById('sliderPrev');
    const sliderNext = document.getElementById('sliderNext');
    const sliderDots = document.getElementById('sliderDots');
    
    let currentSlide = 0;
    let slides = [];
    let autoSlideInterval;

    async function loadSliderImages() {
        try {
            const response = await fetch('/api/slider-images');
            const images = await response.json();
            
            if (images.length === 0) {
                sliderTrack.innerHTML = '<div class="slider-empty">📷 Фотографии скоро появятся...</div>';
                sliderPrev.style.display = 'none';
                sliderNext.style.display = 'none';
                return;
            }
            
            // Create slides
            sliderTrack.innerHTML = images.map((img, index) => `
                <div class="slider-slide">
                    <img src="${img.url}" alt="Фото ${index + 1}" loading="lazy">
                </div>
            `).join('');
            
            slides = document.querySelectorAll('.slider-slide');
            
            // Create dots
            sliderDots.innerHTML = images.map((_, index) => `
                <span class="slider-dot ${index === 0 ? 'active' : ''}" data-index="${index}"></span>
            `).join('');
            
            // Add dot click handlers
            document.querySelectorAll('.slider-dot').forEach(dot => {
                dot.addEventListener('click', () => {
                    goToSlide(parseInt(dot.getAttribute('data-index')));
                });
            });
            
            // Start auto-slide
            startAutoSlide();
            
        } catch (error) {
            console.log('Slider images not loaded:', error);
            sliderTrack.innerHTML = '<div class="slider-empty">📷 Фотографии скоро появятся...</div>';
            sliderPrev.style.display = 'none';
            sliderNext.style.display = 'none';
        }
    }

    function goToSlide(index) {
        if (slides.length === 0) return;
        
        currentSlide = index;
        if (currentSlide >= slides.length) currentSlide = 0;
        if (currentSlide < 0) currentSlide = slides.length - 1;
        
        sliderTrack.style.transform = `translateX(-${currentSlide * 100}%)`;
        
        // Update dots
        document.querySelectorAll('.slider-dot').forEach((dot, i) => {
            dot.classList.toggle('active', i === currentSlide);
        });
    }

    function nextSlide() {
        goToSlide(currentSlide + 1);
    }

    function prevSlide() {
        goToSlide(currentSlide - 1);
    }

    function startAutoSlide() {
        autoSlideInterval = setInterval(nextSlide, 5000);
    }

    function stopAutoSlide() {
        clearInterval(autoSlideInterval);
    }

    sliderPrev.addEventListener('click', () => {
        prevSlide();
        stopAutoSlide();
        startAutoSlide();
    });

    sliderNext.addEventListener('click', () => {
        nextSlide();
        stopAutoSlide();
        startAutoSlide();
    });

    // Touch/swipe support for slider
    let touchStartX = 0;
    let touchEndX = 0;

    sliderTrack.addEventListener('touchstart', (e) => {
        touchStartX = e.changedTouches[0].screenX;
        stopAutoSlide();
    }, { passive: true });

    sliderTrack.addEventListener('touchend', (e) => {
        touchEndX = e.changedTouches[0].screenX;
        handleSwipe();
        startAutoSlide();
    }, { passive: true });

    function handleSwipe() {
        const swipeThreshold = 50;
        const diff = touchStartX - touchEndX;
        
        if (Math.abs(diff) > swipeThreshold) {
            if (diff > 0) {
                nextSlide();
            } else {
                prevSlide();
            }
        }
    }

    // Load slider images
    loadSliderImages();

    // ============ Yandex Map ============
    let yandexMap = null;
    let mapPlacemarks = {};

    function initYandexMap() {
        if (typeof ymaps === 'undefined') {
            // Fallback to iframe if API not loaded
            const mapContainer = document.getElementById('yandexMap');
            if (mapContainer) {
                mapContainer.innerHTML = `
                    <iframe 
                        src="https://yandex.ru/map-widget/v1/?ll=58.52%2C51.27&z=9&pt=58.440637,51.463453,pm2blm~58.449809,51.460475,pm2rdm~58.513509,51.187253,pm2gnm~58.593936,51.076910,pm2orm~58.619006,51.213335,pm2vkm"
                        width="100%" 
                        height="450" 
                        frameborder="0"
                        allowfullscreen>
                    </iframe>
                `;
            }
            return;
        }

        ymaps.ready(function() {
            yandexMap = new ymaps.Map('yandexMap', {
                center: [51.27, 58.52],
                zoom: 9,
                controls: ['zoomControl', 'fullscreenControl']
            });

            // Add placemarks for each location
            Object.keys(CONFIG.locations).forEach(key => {
                const loc = CONFIG.locations[key];
                const placemark = new ymaps.Placemark(
                    [loc.lat, loc.lng],
                    {
                        balloonContentHeader: `<div class="map-balloon-title">${loc.name}</div>`,
                        balloonContentBody: `
                            <div class="map-balloon">
                                <div class="map-balloon-address">${loc.address}</div>
                                <a href="https://yandex.ru/maps/?pt=${loc.lng},${loc.lat}&z=16&l=map" 
                                   target="_blank" 
                                   class="map-balloon-link">
                                    Открыть в Яндекс.Картах
                                </a>
                            </div>
                        `,
                        hintContent: loc.name
                    },
                    {
                        preset: getPresetByKey(key),
                        iconColor: loc.color
                    }
                );

                yandexMap.geoObjects.add(placemark);
                mapPlacemarks[key] = placemark;
            });
        });
    }

    function getPresetByKey(key) {
        const presets = {
            city: 'islands#blueCircleDotIcon',
            day1_venue: 'islands#redDotIcon',
            day2_venue: 'islands#greenDotIcon',
            airport: 'islands#orangeDotIcon',
            railway: 'islands#violetDotIcon'
        };
        return presets[key] || 'islands#blueDotIcon';
    }

    function zoomToLocation(locationKey) {
        if (!yandexMap || !CONFIG.locations[locationKey]) return;

        const loc = CONFIG.locations[locationKey];
        yandexMap.setCenter([loc.lat, loc.lng], 14, {
            duration: 500
        });

        // Open balloon
        if (mapPlacemarks[locationKey]) {
            mapPlacemarks[locationKey].balloon.open();
        }

        // Update active state
        document.querySelectorAll('.location-card').forEach(card => {
            card.classList.remove('active');
            if (card.dataset.location === locationKey) {
                card.classList.add('active');
            }
        });
    }

    // Initialize map
    initYandexMap();

    // Location card click handlers
    document.querySelectorAll('.location-card').forEach(card => {
        card.addEventListener('click', () => {
            const locationKey = card.dataset.location;
            zoomToLocation(locationKey);
            
            // Scroll to map on mobile
            if (window.innerWidth < 992) {
                const mapElement = document.getElementById('yandexMap');
                if (mapElement) {
                    mapElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
            }
        });
    });

    // Legend item click handlers
    document.querySelectorAll('.legend-item').forEach(item => {
        item.addEventListener('click', () => {
            const locationKey = item.dataset.location;
            if (locationKey) {
                zoomToLocation(locationKey);
            }
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

    // ============ RSVP Form (consolidated) ============
    // Remove duplicated declarations and handlers; keep a single, consistent implementation.
    (function() {
        const rsvpForm = document.getElementById('rsvpForm');
        const conditionalFields = document.getElementById('conditionalFields');
        const attendingRadios = Array.from(document.querySelectorAll('input[name="attending"]'));

        // Ensure conditional fields reflect current selection
        function updateConditional() {
            const checked = document.querySelector('input[name="attending"]:checked');
            if (checked && checked.value === 'yes') {
                // show using className used by CSS or inline style as fallback
                conditionalFields.classList.add('show');
                conditionalFields.style.display = '';
            } else {
                conditionalFields.classList.remove('show');
                conditionalFields.style.display = 'none';
            }
        }

        attendingRadios.forEach(radio => {
            radio.addEventListener('change', updateConditional);
        });
        updateConditional();

        // Single toast implementation (type can be 'success' or 'error')
        function showToast(message, type = 'success') {
            const toast = document.getElementById('toast');
            if (!toast) return;
            const toastMessage = toast.querySelector('.toast-message');
            toastMessage.textContent = message;
            toast.className = `toast ${type} show`;
            setTimeout(() => toast.classList.remove('show'), 4000);
        }

        // Submit handler: serialize form to JSON and POST (send attending as "yes"/"no")
        if (rsvpForm) {
            rsvpForm.addEventListener('submit', async (e) => {
                e.preventDefault();

                const formData = new FormData(rsvpForm);

                // Build payload matching server expectations (phone + telegram)
                const payload = {
                    first_name: formData.get('first_name') || '',
                    last_name: formData.get('last_name') || '',
                    phone: formData.get('phone') || '',
                    telegram: formData.get('telegram') || '',
                    attending: formData.get('attending') || '', // keep as "yes" or "no"
                    guests_count: formData.get('guests_count') || 1,
                    children: formData.get('children') || '',
                    food_preferences: formData.get('food_preferences') || ''
                };

                // Basic client-side validation
                if (!payload.attending) {
                    showToast('Пожалуйста, укажите, придёте ли вы.', 'error');
                    return;
                }
                if (!payload.phone || !payload.telegram) {
                    showToast('Телефон и Telegram обязательны.', 'error');
                    return;
                }

                try {
                    const resp = await fetch('/api/rsvp', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(payload)
                    });
                    const json = await resp.json().catch(() => ({}));

                    if (resp.ok && json.status === 'success') {
                        showToast(json.message || 'Анкета отправлена', 'success');
                        rsvpForm.reset();
                        updateConditional();
                    } else {
                        showToast(json.message || 'Ошибка при отправке.', 'error');
                    }
                } catch (err) {
                    console.error(err);
                    showToast('Ошибка сети. Попробуйте позже.', 'error');
                }
            });
        }
    })();

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
