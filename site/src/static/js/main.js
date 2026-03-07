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

    // ============ RSVP Form (new) ============
    (function () {
        const form = document.getElementById('rsvpForm');
        if (!form) return;

        const attendingRadios  = () => Array.from(form.querySelectorAll('input[name="attending"]'));
        const withOthersRadios = () => Array.from(form.querySelectorAll('input[name="with_others"]'));
        const rsvpWithGroup    = document.getElementById('rsvpWithGroup');
        const familySection    = document.getElementById('rsvpFamilySection');
        const familyList       = document.getElementById('familyMembersList');
        const addBtn           = document.getElementById('addFamilyMember');

        let memberCounter = 0;

        // ---- visibility helpers ----
        function getVal(radios) {
            const c = radios().find(r => r.checked);
            return c ? c.value : null;
        }

        function refreshVisibility() {
            const attending  = getVal(attendingRadios);
            const withOthers = getVal(withOthersRadios);

            // Show "alone / family" only when attending
            rsvpWithGroup.style.display = attending === 'yes' ? '' : 'none';
            if (attending !== 'yes') {
                // reset with_others selection
                withOthersRadios().forEach(r => r.checked = false);
            }

            // Show family section
            const showFamily = attending === 'yes' && withOthers === 'family';
            familySection.style.display = showFamily ? '' : 'none';
            if (!showFamily) familyList.innerHTML = '';
        }

        attendingRadios().forEach(r  => r.addEventListener('change', refreshVisibility));
        // delegate for dynamically added radios
        form.addEventListener('change', function (e) {
            if (e.target.name === 'with_others') refreshVisibility();
        });

        // ---- family member card ----
        function createMemberCard() {
            memberCounter++;
            const idx = memberCounter;

            const card = document.createElement('div');
            card.className = 'family-member-card';
            card.dataset.member = idx;

            card.innerHTML = `
                <div class="family-member-card-header">
                    <span class="family-member-card-title">Сопровождающий ${idx}</span>
                    <button type="button" class="family-member-remove" aria-label="Удалить">✕</button>
                </div>

                <div class="form-group">
                    <label>Роль *</label>
                    <div class="role-selector">
                        <button type="button" class="role-btn" data-role="partner">💑 Вторая половинка</button>
                        <button type="button" class="role-btn" data-role="child">👶 Ребёнок</button>
                    </div>
                </div>

                <div class="member-fields" data-fields-for="${idx}" style="display:none"></div>
            `;

            // Role buttons
            card.querySelectorAll('.role-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    card.querySelectorAll('.role-btn').forEach(b => b.classList.remove('active'));
                    btn.classList.add('active');
                    card.dataset.role = btn.dataset.role;
                    renderMemberFields(card, btn.dataset.role);
                });
            });

            // Remove button
            card.querySelector('.family-member-remove').addEventListener('click', () => {
                card.remove();
                renumberCards();
            });

            return card;
        }

        function renderMemberFields(card, role) {
            const container = card.querySelector('.member-fields');
            container.style.display = '';

            if (role === 'child') {
                container.innerHTML = `
                    <div class="form-row">
                        <div class="form-group">
                            <label>Имя *</label>
                            <input type="text" name="member_first_name" required placeholder="Имя ребёнка">
                        </div>
                        <div class="form-group">
                            <label>Фамилия *</label>
                            <input type="text" name="member_last_name" required placeholder="Фамилия ребёнка">
                        </div>
                    </div>
                `;
            } else {
                // partner
                container.innerHTML = `
                    <div class="form-row">
                        <div class="form-group">
                            <label>Имя *</label>
                            <input type="text" name="member_first_name" required>
                        </div>
                        <div class="form-group">
                            <label>Фамилия *</label>
                            <input type="text" name="member_last_name" required>
                        </div>
                    </div>
                    <div class="form-row">
                        <div class="form-group">
                            <label>Телефон *</label>
                            <input type="text" name="member_phone" required placeholder="+7 (999) 123-45-67">
                        </div>
                        <div class="form-group">
                            <label>Telegram *</label>
                            <input type="text" name="member_telegram" required placeholder="@username">
                        </div>
                    </div>
                `;
            }
        }

        function renumberCards() {
            familyList.querySelectorAll('.family-member-card').forEach((card, i) => {
                card.querySelector('.family-member-card-title').textContent = `Сопровождающий ${i + 1}`;
            });
        }

        addBtn.addEventListener('click', () => {
            familyList.appendChild(createMemberCard());
        });

        // ---- collect & submit ----
        function collectMembers() {
            const members = [];
            familyList.querySelectorAll('.family-member-card').forEach(card => {
                const role = card.dataset.role;
                if (!role) return; // no role selected yet — skip (validation will catch it)

                const fn = card.querySelector('[name="member_first_name"]')?.value.trim() || '';
                const ln = card.querySelector('[name="member_last_name"]')?.value.trim() || '';
                const ph = card.querySelector('[name="member_phone"]')?.value.trim()      || '';
                const tg = card.querySelector('[name="member_telegram"]')?.value.trim()   || '';

                members.push({ fn, ln, ph, tg, role });
            });
            return members;
        }

        function validateForm() {
            const fn = form.querySelector('#firstName').value.trim();
            const ln = form.querySelector('#lastName').value.trim();
            const ph = form.querySelector('#phone').value.trim();
            const tg = form.querySelector('#telegram').value.trim();
            const attending = getVal(attendingRadios);

            if (!fn || !ln) { showToast('Введите имя и фамилию.', 'error'); return false; }
            if (!ph)          { showToast('Введите номер телефона.', 'error'); return false; }
            if (!tg)          { showToast('Введите Telegram-ник.', 'error'); return false; }
            if (!attending)   { showToast('Укажите, придёте ли вы.', 'error'); return false; }

            if (attending === 'yes') {
                const wo = getVal(withOthersRadios);
                if (!wo) { showToast('Укажите, придёте один или с кем-то.', 'error'); return false; }

                if (wo === 'family') {
                    const cards = familyList.querySelectorAll('.family-member-card');
                    if (cards.length === 0) {
                        showToast('Добавьте хотя бы одного сопровождающего.', 'error');
                        return false;
                    }
                    for (const card of cards) {
                        const role = card.dataset.role;
                        if (!role) { showToast('Выберите роль для каждого сопровождающего.', 'error'); return false; }
                        const mfn = card.querySelector('[name="member_first_name"]')?.value.trim();
                        const mln = card.querySelector('[name="member_last_name"]')?.value.trim();
                        if (!mfn || !mln) { showToast('Введите имя и фамилию для каждого сопровождающего.', 'error'); return false; }
                        if (role === 'partner') {
                            const mph = card.querySelector('[name="member_phone"]')?.value.trim();
                            const mtg = card.querySelector('[name="member_telegram"]')?.value.trim();
                            if (!mph || !mtg) { showToast('Введите телефон и Telegram для второй половинки.', 'error'); return false; }
                        }
                    }
                }
            }
            return true;
        }

        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            if (!validateForm()) return;

            const attending   = getVal(attendingRadios);
            const isAttending = attending === 'yes';
            const withOthers  = getVal(withOthersRadios);

            const mainPerson = {
                first_name:       form.querySelector('#firstName').value.trim(),
                second_name:      form.querySelector('#lastName').value.trim(),
                phone_number:     form.querySelector('#phone').value.trim(),
                tg_username:      form.querySelector('#telegram').value.trim(),
                telegram_id:      null,
                chat_id:          null,
                role:             'FAMALY_HEAD',
                main_account:     null,
                is_main_account:  true,
                is_going_on_event: isAttending
            };

            const submitBtn = document.getElementById('rsvpSubmitBtn');
            submitBtn.disabled = true;
            submitBtn.textContent = 'Отправляем...';

            try {
                let resp;

                if (!isAttending || withOthers === 'alone' || !withOthers) {
                    // Single member
                    resp = await fetch('/api/members', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(mainPerson)
                    });
                } else {
                    // Family
                    const rawMembers = collectMembers();
                    const family = [mainPerson];
                    
                    
                    rawMembers.forEach((m, i) => {
                        const phone = m.ph ? m.ph.trim() : '';
                        if (!phone) {
                            family.push({
                                first_name:       m.fn,
                                second_name:      m.ln,
                                tg_username:      m.tg ? m.tg.trim() : null,
                                telegram_id:      null,
                                chat_id:          null,
                                role:             m.role === 'child' ? 'CHILD' : 'FAMALY_TAIL',
                                main_account:     null,
                                is_main_account:  false,
                                is_going_on_event: true
                            });
                        } else {
                            family.push({
                                first_name:       m.fn,
                                second_name:      m.ln,
                                phone_number:     m.ph ? m.ph.trim() : null ,
                                tg_username:      m.tg ? m.tg.trim() : null,
                                telegram_id:      null,
                                chat_id:          null,
                                role:             m.role === 'child' ? 'CHILD' : 'FAMALY_TAIL',
                                main_account:     null,
                                is_main_account:  false,
                                is_going_on_event: true
                            });
                        }
                    });

                    

                    resp = await fetch('/api/members/family', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(family)
                    });
                }

                const json = await resp.json().catch(() => ({}));

                if (resp.ok) {
                    showToast(json.message || 'Анкета отправлена! 🎉', 'success');
                    form.reset();
                    familyList.innerHTML = '';
                    refreshVisibility();
                } else {
                    showToast(json.message || json.detail || 'Ошибка при отправке.', 'error');
                }
            } catch (err) {
                console.error(err);
                showToast('Ошибка сети. Попробуйте позже.', 'error');
            } finally {
                submitBtn.disabled = false;
                submitBtn.textContent = 'Отправить';
            }
        });

        refreshVisibility();
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
