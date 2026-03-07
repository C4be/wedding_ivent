import json
import os
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import requests

app = Flask(__name__, 
            template_folder='templates',
            static_folder='static')
CORS(app)

CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', 'materials', 'site.info.json')
IMAGES_PATH = os.path.join(os.path.dirname(__file__), '..', 'materials', 'imgs')
SLIDER_PATH = os.path.join(os.path.dirname(__file__), 'static', 'images', 'slider')
DB_SERVICE_URL = os.environ.get('DB_SERVICE_URL', 'http://wedding-db-service:8000')

def load_config():
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_config(config):
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


@app.route('/')
def index():
    config = load_config()
    return render_template('index.html', config=config)

# ============ REST API ============

@app.route('/api/config', methods=['GET'])
def get_config():
    """Get current site configuration"""
    return jsonify(load_config())

@app.route('/api/config', methods=['PUT'])
def update_config():
    """Update site configuration"""
    try:
        new_config = request.json
        save_config(new_config)
        return jsonify({"status": "success", "message": "Config updated"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/config/<section>', methods=['PATCH'])
def update_section(section):
    """Update specific section of config"""
    try:
        config = load_config()
        if section in config:
            config[section].update(request.json)
            save_config(config)
            return jsonify({"status": "success", "message": f"Section {section} updated"})
        return jsonify({"status": "error", "message": "Section not found"}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/rsvp', methods=['POST'])
def submit_rsvp():
    """Submit RSVP form to Telegram bot"""
    try:
        data = request.json or {}
        config = load_config()
        
        # Extract contacts (form now has separate phone and telegram fields)
        phone = data.get('phone', '').strip()
        telegram_contact = data.get('telegram', '').strip()
        
        # Basic validation
        if not phone or not telegram_contact:
            return jsonify({"status": "error", "message": "Phone and Telegram are required"}), 400
        
        # Determine attendance (form radios send "yes" or "no")
        attending_value = data.get('attending')
        is_attending = True if str(attending_value).lower() == 'yes' else False
        
        # Format message for Telegram
        contact_display = f"Телефон: {phone}\nTelegram: {telegram_contact}"
        message = f"""
🎊 *Новая анкета гостя!*

👤 *Имя:* {data.get('first_name', 'Не указано')}
👤 *Фамилия:* {data.get('last_name', 'Не указано')}
📱 *Контакт:* {contact_display}
✅ *Статус:* {'Буду' if is_attending else 'Не смогу'}
👥 *Количество гостей:* {data.get('guests_count', 1)}
👶 *Дети:* {data.get('children', 'Нет')}
🍽 *Пожелания по еде:* {data.get('food_preferences', 'Нет')}
        """
        
        # Send to Telegram
        bot_token = config['telegram_bot']['token']
        chat_id = config['telegram_bot']['chat_id']
        
        if bot_token != "YOUR_BOT_TOKEN":
            requests.post(
                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": message,
                    "parse_mode": "Markdown"
                }
            )
        
        return jsonify({"status": "success", "message": "RSVP submitted"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/question', methods=['POST'])
def submit_question():
    """Submit question to Telegram bot"""
    try:
        data = request.json
        message = f"""
❓ *Новый вопрос от гостя!*

👤 *От:* {data.get('name', 'Аноним')}
📱 *Контакт:* {data.get('contact', 'Не указан')}

💬 *Вопрос:*
{data.get('question', '')}
        """
        
        requests.post(
            f"http://wedding-bot:5555/form",
            json={
                "text": message,
                "parse_mode": "Markdown"
            }
        )
        
        return jsonify({"status": "success", "message": "Question submitted"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/gallery', methods=['GET'])
def get_gallery():
    """Get gallery images"""
    config = load_config()
    return jsonify(config['images'].get('gallery', []))

@app.route('/api/gallery', methods=['POST'])
def add_to_gallery():
    """Add image to gallery (for bot integration)"""
    try:
        data = request.json
        config = load_config()
        
        if 'gallery' not in config['images']:
            config['images']['gallery'] = []
        
        config['images']['gallery'].append({
            "url": data.get('url'),
            "caption": data.get('caption', ''),
            "added_at": datetime.now().isoformat()
        })
        
        save_config(config)
        return jsonify({"status": "success", "message": "Image added to gallery"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/faq', methods=['POST'])
def add_faq():
    """Add FAQ item"""
    try:
        data = request.json
        config = load_config()
        
        config['faq'].append({
            "question": data.get('question'),
            "answer": data.get('answer')
        })
        
        save_config(config)
        return jsonify({"status": "success", "message": "FAQ added"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/slider-images', methods=['GET'])
def get_slider_images():
    """Get images from slider folder"""
    try:
        images = []
        if os.path.exists(SLIDER_PATH):
            allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
            for filename in sorted(os.listdir(SLIDER_PATH)):
                ext = os.path.splitext(filename)[1].lower()
                if ext in allowed_extensions:
                    images.append({
                        'url': f'/static/images/slider/{filename}',
                        'filename': filename
                    })
        return jsonify(images)
    except Exception as e:
        return jsonify([])

@app.route('/api/members', methods=['POST'])
def create_member():
    """Proxy single member registration to wedding-db-service"""
    try:
        data = request.json or {}
        resp = requests.post(
            f"{DB_SERVICE_URL}/members/",
            json=data,
            timeout=10
        )
        return jsonify(resp.json()), resp.status_code
    except requests.exceptions.ConnectionError:
        return jsonify({"status": "error", "message": "DB service unavailable"}), 503
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/members/family', methods=['POST'])
def create_family():
    """Proxy family registration to wedding-db-service"""
    try:
        data = request.json or []
        resp = requests.post(
            f"{DB_SERVICE_URL}/members/family",
            json=data,
            timeout=10
        )
        return jsonify(resp.json()), resp.status_code
    except requests.exceptions.ConnectionError:
        return jsonify({"status": "error", "message": "DB service unavailable"}), 503
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.errorhandler(400)
def bad_request(error):
    """
    Render a friendly 400 page.
    Prefer explicit ?error=... query parameter when available (useful for testing).
    """
    err_text = request.args.get('error')
    if not err_text:
        err_text = getattr(error, 'description', None) or str(error)
    return render_template('400.html', error_text=err_text), 400

@app.route('/400')
def show_400():
    """
    Test route: open /400?error=Some%20text to preview the 400 page.
    """
    err_text = request.args.get('error', '')
    return render_template('400.html', error_text=err_text), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
