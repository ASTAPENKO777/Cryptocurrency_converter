from flask import Flask, render_template, request, jsonify
from werkzeug.exceptions import BadRequest
import requests
import time

app = Flask(__name__)

DISPLAY_CRYPTO_CURRENCIES = ['BTC', 'ETH', 'BNB', 'XRP', 'SOL', 'ADA', 'DOGE', 'DOT', 'MATIC', 'LTC']
DISPLAY_FIAT_CURRENCIES = ['USD', 'EUR', 'UAH', 'GBP', 'JPY', 'CAD', 'AUD', 'CNY']

COINGECKO_CRYPTO_IDS = {
    'BTC': 'bitcoin',
    'ETH': 'ethereum',
    'BNB': 'binancecoin',
    'XRP': 'ripple',
    'SOL': 'solana',
    'ADA': 'cardano',
    'DOGE': 'dogecoin',
    'DOT': 'polkadot',
    'MATIC': 'matic-network',
    'LTC': 'litecoin'
}

COINGECKO_FIAT_CURRENCIES = {
    'USD': 'usd',
    'EUR': 'eur',
    'UAH': 'uah',
    'GBP': 'gbp',
    'JPY': 'jpy',
    'CAD': 'cad',
    'AUD': 'aud',
    'CNY': 'cny'
}

RATE_CACHE = {}
CACHE_TIMEOUT = 300  


def get_coingecko_rates(crypto_id, vs_currency):
    """Отримання курсів з CoinGecko API"""
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={crypto_id}&vs_currencies={vs_currency}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        app.logger.error(f"CoinGecko API error: {str(e)}")
        return None


@app.route('/')
def index():
    return render_template('index.html',
                        crypto_currencies=DISPLAY_CRYPTO_CURRENCIES,
                        fiat_currencies=DISPLAY_FIAT_CURRENCIES)


@app.route('/convert', methods=['POST'])
def convert():
    try:
        data = request.get_json()
        if not data:
            raise BadRequest('No data provided')
        

        from_currency = data.get('from_currency', '')
        to_currency = data.get('to_currency', '')
        amount = data.get('amount')
        
        if not all([from_currency, to_currency, amount]):
            raise BadRequest('Missing required parameters')
        
        try:
            amount = float(amount)
            if amount <= 0:
                raise ValueError('Amount must be positive')
        except ValueError:
            raise BadRequest('Invalid amount value')
        

        is_crypto_to_fiat = from_currency in COINGECKO_CRYPTO_IDS and to_currency in COINGECKO_FIAT_CURRENCIES
        is_fiat_to_crypto = from_currency in COINGECKO_FIAT_CURRENCIES and to_currency in COINGECKO_CRYPTO_IDS
        
        if not (is_crypto_to_fiat or is_fiat_to_crypto):
            return jsonify({
                'error': f'Unsupported conversion: {from_currency} to {to_currency}'
            }), 400
        

        cache_key = f"{from_currency}_{to_currency}"
        current_time = time.time()
        
        if cache_key in RATE_CACHE and current_time - RATE_CACHE[cache_key]['timestamp'] < CACHE_TIMEOUT:
            rate = RATE_CACHE[cache_key]['rate']
        else:
            if is_crypto_to_fiat:
                crypto_id = COINGECKO_CRYPTO_IDS[from_currency]
                vs_currency = COINGECKO_FIAT_CURRENCIES[to_currency]
                data = get_coingecko_rates(crypto_id, vs_currency)
                if not data or crypto_id not in data:
                    return jsonify({'error': 'Failed to get exchange rate'}), 500
                rate = data[crypto_id][vs_currency]
            else: 
                crypto_id = COINGECKO_CRYPTO_IDS[to_currency]
                vs_currency = COINGECKO_FIAT_CURRENCIES[from_currency]
                data = get_coingecko_rates(crypto_id, vs_currency)
                if not data or crypto_id not in data:
                    return jsonify({'error': 'Failed to get exchange rate'}), 500
                rate = 1 / data[crypto_id][vs_currency]
            
            RATE_CACHE[cache_key] = {
                'rate': rate,
                'timestamp': current_time
            }
        

        result = amount * rate
        
        return jsonify({
            'amount': amount,
            'from_currency': from_currency,
            'to_currency': to_currency,
            'result': round(result, 6),
            'rate': rate
        })
        
    except BadRequest as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        app.logger.error(f'Conversion error: {str(e)}')
        return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    app.run(debug=True)