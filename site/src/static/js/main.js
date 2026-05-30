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

    const safeGalleryEnabled = typeof CONFIG.galleryEnabled === 'boolean' ? CONFIG.galleryEnabled : true;
    if (!safeGalleryEnabled) {
        document.querySelectorAll('[data-gallery-nav="1"]').forEach(el => el.remove());
    }

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

    function setPreferencesHeadNames(firstName, secondName) {
        const prefFirstInput = document.getElementById('prefHeadFirstName');
        const prefSecondInput = document.getElementById('prefHeadSecondName');
        if (!prefFirstInput || !prefSecondInput) return;
        prefFirstInput.value = firstName || '';
        prefSecondInput.value = secondName || '';
    }

    // ============ Family Registration Form ============
    (function () {
        const form = document.getElementById('familyRegistrationForm');
        if (!form) return;

        const headFirstInput = document.getElementById('headFirstName');
        const headSecondInput = document.getElementById('headSecondName');
        const memberFirstInput = document.getElementById('memberFirstName');
        const memberSecondInput = document.getElementById('memberSecondName');
        const memberRoleInput = document.getElementById('memberRole');
        const memberPhoneInput = document.getElementById('memberPhone');
        const memberAttendingInput = document.getElementById('memberAttending');
        const registerBtn = document.getElementById('registerFamilyBtn');
        const deleteFamilyBtn = document.getElementById('deleteFamilyBtn');
        const addMemberBtn = document.getElementById('addFamilyMemberBtn');
        const membersList = document.getElementById('familyMembersList');
        const familyKeyHint = document.getElementById('familyKeyHint');

        let activeFamily = null;

        function normalizeName(value) {
            return String(value || '').trim().replace(/\s+/g, ' ');
        }

        function normalizeNameKey(value) {
            return normalizeName(value).toLowerCase();
        }

        function buildHeadKey(firstName, secondName) {
            return `${normalizeNameKey(firstName)}::${normalizeNameKey(secondName)}`;
        }

        function getHeadData() {
            return {
                head_first_name: normalizeName(headFirstInput.value),
                head_second_name: normalizeName(headSecondInput.value)
            };
        }

        function isActiveHeadSelected() {
            if (!activeFamily) return false;
            const head = getHeadData();
            return buildHeadKey(head.head_first_name, head.head_second_name) === activeFamily.family_key;
        }

        function updateFamilyHint(text, success = false) {
            familyKeyHint.textContent = text;
            familyKeyHint.classList.toggle('active', success);
        }

        function roleLabel(role) {
            const map = {
                head: 'Глава семьи',
                partner: 'Партнёр',
                child: 'Ребёнок',
                guest: 'Гость',
                member: 'Участник'
            };
            return map[role] || role;
        }

        function renderMembers(family) {
            const members = family?.members || [];
            if (members.length === 0) {
                membersList.innerHTML = '<p class="family-members-empty">Список пока пуст.</p>';
                return;
            }

            membersList.innerHTML = members.map((member) => {
                const canDelete = member.role !== 'head';
                const phone = member.phone ? `<span>Телефон: ${member.phone}</span>` : '';
                const attendingText = member.attending ? '✅ Придёт' : '❌ Не придёт';

                return `
                    <div class="family-member-item">
                        <div class="family-member-main">
                            <strong>${member.first_name} ${member.second_name}</strong>
                            <span>${roleLabel(member.role)}</span>
                            <span>${attendingText}</span>
                            ${phone}
                        </div>
                        ${canDelete ? `
                            <div class="form-actions family-member-actions" style="margin-top: 0; gap: 8px;">
                                <button
                                    type="button"
                                    class="btn btn-outline btn-sm family-member-icon-btn family-member-edit"
                                    data-first-name="${member.first_name}"
                                    data-second-name="${member.second_name}"
                                    data-role="${member.role || 'member'}"
                                    data-phone="${member.phone || ''}"
                                    data-attending="${member.attending ? 'yes' : 'no'}"
                                >✏️</button>
                                <button type="button" class="btn btn-outline btn-sm family-member-icon-btn family-member-delete" data-first-name="${member.first_name}" data-second-name="${member.second_name}">🗑️</button>
                            </div>
                        ` : ''}
                    </div>
                `;
            }).join('');

            setPreferencesHeadNames(family.head_first_name, family.head_second_name);
        }

        async function registerFamily() {
            const head = getHeadData();
            if (!head.head_first_name || !head.head_second_name) {
                showToast('Введите имя и фамилию главы семьи.', 'error');
                return null;
            }

            registerBtn.disabled = true;
            registerBtn.textContent = 'Сохраняем...';

            try {
                const response = await fetch('/api/families/register', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(head)
                });

                const result = await response.json().catch(() => ({}));
                if (!response.ok || result.status !== 'success') {
                    showToast(result.message || 'Не удалось создать семейную группу.', 'error');
                    return null;
                }

                activeFamily = result.family;
                renderMembers(activeFamily);
                setPreferencesHeadNames(activeFamily.head_first_name, activeFamily.head_second_name);
                updateFamilyHint(`Семейная группа активна: ${activeFamily.head_first_name} ${activeFamily.head_second_name}`, true);
                showToast('Семейная группа готова. Можно добавлять участников.', 'success');
                return activeFamily;
            } catch (error) {
                showToast('Ошибка сети. Попробуйте позже.', 'error');
                return null;
            } finally {
                registerBtn.disabled = false;
                registerBtn.textContent = 'Найти/создать семейную группу';
            }
        }

        async function addOrUpdateMember() {
            if (!isActiveHeadSelected()) {
                showToast('Сначала нажмите "Найти/создать семейную группу".', 'error');
                return;
            }

            const memberFirst = normalizeName(memberFirstInput.value);
            const memberSecond = normalizeName(memberSecondInput.value);

            if (!memberFirst || !memberSecond) {
                showToast('Введите имя и фамилию участника.', 'error');
                return;
            }

            const payload = {
                ...getHeadData(),
                member_first_name: memberFirst,
                member_second_name: memberSecond,
                role: memberRoleInput.value || 'member',
                phone: normalizeName(memberPhoneInput.value),
                attending: memberAttendingInput.value === 'yes'
            };

            addMemberBtn.disabled = true;
            addMemberBtn.textContent = 'Сохраняем...';

            try {
                const response = await fetch('/api/families/member', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });

                const result = await response.json().catch(() => ({}));
                if (!response.ok || result.status !== 'success') {
                    showToast(result.message || 'Не удалось сохранить участника.', 'error');
                    return;
                }

                activeFamily = result.family;
                renderMembers(activeFamily);
                memberFirstInput.value = '';
                memberSecondInput.value = '';
                memberPhoneInput.value = '';
                memberRoleInput.value = 'member';
                memberAttendingInput.value = 'yes';
                showToast('Участник сохранён.', 'success');
            } catch (error) {
                showToast('Ошибка сети. Попробуйте позже.', 'error');
            } finally {
                addMemberBtn.disabled = false;
                addMemberBtn.textContent = 'Добавить / обновить участника';
            }
        }

        async function removeMember(memberFirstName, memberSecondName) {
            if (!isActiveHeadSelected()) {
                showToast('Сначала активируйте семью повторно.', 'error');
                return;
            }

            try {
                const response = await fetch('/api/families/member', {
                    method: 'DELETE',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        ...getHeadData(),
                        member_first_name: memberFirstName,
                        member_second_name: memberSecondName
                    })
                });

                const result = await response.json().catch(() => ({}));
                if (!response.ok || result.status !== 'success') {
                    showToast(result.message || 'Не удалось удалить участника.', 'error');
                    return;
                }

                activeFamily = result.family;
                renderMembers(activeFamily);
                showToast('Участник удалён.', 'success');
            } catch (error) {
                showToast('Ошибка сети. Попробуйте позже.', 'error');
            }
        }

        async function deleteFamilyGroup() {
            const head = getHeadData();
            if (!head.head_first_name || !head.head_second_name) {
                showToast('Введите имя и фамилию главы семьи.', 'error');
                return;
            }

            const confirmDelete = window.confirm(
                `Удалить семейную группу ${head.head_first_name} ${head.head_second_name} и все связанные данные?`
            );
            if (!confirmDelete) return;

            deleteFamilyBtn.disabled = true;
            const oldText = deleteFamilyBtn.textContent;
            deleteFamilyBtn.textContent = 'Удаляем...';

            try {
                const response = await fetch('/api/families/register', {
                    method: 'DELETE',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(head)
                });

                const result = await response.json().catch(() => ({}));
                if (!response.ok || result.status !== 'success') {
                    showToast(result.message || 'Не удалось удалить семейную группу.', 'error');
                    return;
                }

                activeFamily = null;
                memberFirstInput.value = '';
                memberSecondInput.value = '';
                memberPhoneInput.value = '';
                memberRoleInput.value = 'member';
                memberAttendingInput.value = 'yes';
                membersList.innerHTML = '<p class="family-members-empty">Список пока пуст.</p>';
                updateFamilyHint('Семейная группа удалена. Можно создать новую.', false);
                showToast('Семейная группа удалена.', 'success');
            } catch (error) {
                showToast('Ошибка сети. Попробуйте позже.', 'error');
            } finally {
                deleteFamilyBtn.disabled = false;
                deleteFamilyBtn.textContent = oldText;
            }
        }

        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            await registerFamily();
        });

        addMemberBtn.addEventListener('click', async () => {
            await addOrUpdateMember();
        });

        if (deleteFamilyBtn) {
            deleteFamilyBtn.addEventListener('click', async () => {
                await deleteFamilyGroup();
            });
        }

        membersList.addEventListener('click', async (e) => {
            const editBtn = e.target.closest('.family-member-edit');
            if (editBtn) {
                memberFirstInput.value = editBtn.dataset.firstName || '';
                memberSecondInput.value = editBtn.dataset.secondName || '';
                memberRoleInput.value = editBtn.dataset.role || 'member';
                memberPhoneInput.value = editBtn.dataset.phone || '';
                memberAttendingInput.value = editBtn.dataset.attending || 'yes';
                showToast('Данные участника подставлены в форму.', 'success');
                addMemberBtn.scrollIntoView({ behavior: 'smooth', block: 'center' });
                return;
            }

            const btn = e.target.closest('.family-member-delete');
            if (!btn) return;
            const memberFirstName = btn.dataset.firstName || '';
            const memberSecondName = btn.dataset.secondName || '';
            if (!memberFirstName || !memberSecondName) return;
            await removeMember(memberFirstName, memberSecondName);
        });

        [headFirstInput, headSecondInput].forEach((input) => {
            input.addEventListener('input', () => {
                if (!activeFamily) return;
                if (!isActiveHeadSelected()) {
                    updateFamilyHint('Вы изменили данные главы семьи. Нажмите "Найти/создать семейную группу" снова.', false);
                }
            });
        });

    })();

    // ============ Family Preferences Form ============
    (function () {
        const form = document.getElementById('preferencesForm');
        if (!form) return;

        const headFirstInput = document.getElementById('prefHeadFirstName');
        const headSecondInput = document.getElementById('prefHeadSecondName');
        const drinksInput = document.getElementById('prefDrinks');
        const musicInput = document.getElementById('prefMusic');
        const foodInput = document.getElementById('prefFood');
        const notesInput = document.getElementById('prefNotes');
        const loadBtn = document.getElementById('loadPreferencesBtn');
        const saveBtn = document.getElementById('savePreferencesBtn');

        function getHeadData() {
            return {
                head_first_name: String(headFirstInput.value || '').trim(),
                head_second_name: String(headSecondInput.value || '').trim()
            };
        }

        function fillPreferences(preferences) {
            drinksInput.value = preferences?.drinks || '';
            musicInput.value = preferences?.music || '';
            foodInput.value = preferences?.food || '';
            notesInput.value = preferences?.notes || '';
        }

        async function loadPreferences() {
            const head = getHeadData();
            if (!head.head_first_name || !head.head_second_name) {
                showToast('Введите имя и фамилию главы семьи.', 'error');
                return;
            }

            loadBtn.disabled = true;
            loadBtn.textContent = 'Загрузка...';

            try {
                const params = new URLSearchParams(head);
                const response = await fetch(`/api/preferences?${params.toString()}`);
                const result = await response.json().catch(() => ({}));

                if (!response.ok || result.status !== 'success') {
                    showToast(result.message || 'Не удалось загрузить предпочтения.', 'error');
                    return;
                }

                fillPreferences(result.preferences);
                showToast('Текущие предпочтения загружены.', 'success');
            } catch (error) {
                showToast('Ошибка сети. Попробуйте позже.', 'error');
            } finally {
                loadBtn.disabled = false;
                loadBtn.textContent = 'Загрузить текущие данные';
            }
        }

        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const head = getHeadData();

            if (!head.head_first_name || !head.head_second_name) {
                showToast('Введите имя и фамилию главы семьи.', 'error');
                return;
            }

            const payload = {
                ...head,
                drinks: String(drinksInput.value || '').trim(),
                music: String(musicInput.value || '').trim(),
                food: String(foodInput.value || '').trim(),
                notes: String(notesInput.value || '').trim()
            };

            saveBtn.disabled = true;
            saveBtn.textContent = 'Сохраняем...';

            try {
                const response = await fetch('/api/preferences', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const result = await response.json().catch(() => ({}));

                if (!response.ok || result.status !== 'success') {
                    showToast(result.message || 'Не удалось сохранить предпочтения.', 'error');
                    return;
                }

                showToast('Предпочтения сохранены.', 'success');
            } catch (error) {
                showToast('Ошибка сети. Попробуйте позже.', 'error');
            } finally {
                saveBtn.disabled = false;
                saveBtn.textContent = 'Сохранить предпочтения';
            }
        });

        loadBtn.addEventListener('click', async () => {
            await loadPreferences();
        });
    })();

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
        if (!safeGalleryEnabled) {
            return;
        }
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

    // ============ Family Invitation Download ============
    (function () {
        const btn = document.getElementById('downloadInvitationBtn');
        const firstInput = document.getElementById('invitationHeadFirstName');
        const secondInput = document.getElementById('invitationHeadSecondName');
        if (!btn || !firstInput || !secondInput) return;

        btn.addEventListener('click', async () => {
            const first = String(firstInput.value || '').trim();
            const second = String(secondInput.value || '').trim();
            if (!first || !second) {
                showToast('Введите имя и фамилию главы семьи.', 'error');
                return;
            }

            btn.disabled = true;
            const originalText = btn.textContent;
            btn.textContent = 'Готовим PDF...';

            try {
                const params = new URLSearchParams({
                    head_first_name: first,
                    head_second_name: second,
                });

                const response = await fetch(`/api/invitation/download?${params.toString()}`);
                if (!response.ok) {
                    let message = 'Не удалось сформировать приглашение.';
                    try {
                        const err = await response.json();
                        if (err?.message) message = err.message;
                    } catch (e) {
                        // ignore
                    }
                    showToast(message, 'error');
                    return;
                }

                const blob = await response.blob();
                const objectUrl = URL.createObjectURL(blob);
                const link = document.createElement('a');
                link.href = objectUrl;
                link.download = `invitation_${second}_${first}.pdf`;
                document.body.appendChild(link);
                link.click();
                link.remove();
                URL.revokeObjectURL(objectUrl);
                showToast('Приглашение готово и скачано.', 'success');
            } catch (error) {
                showToast('Ошибка сети. Попробуйте позже.', 'error');
            } finally {
                btn.disabled = false;
                btn.textContent = originalText;
            }
        });
    })();

    loadGallery();
});
