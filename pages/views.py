from django.views.generic import TemplateView, View
from django.http import HttpResponse, HttpResponseRedirect
from django.conf import settings
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
import datetime
import base64
import plaid
import time
import json

client = plaid.Client(client_id = settings.PLAID_CLIENT_ID,
                      secret=settings.PLAID_SECRET,
                      public_key=settings.PLAID_PUBLIC_KEY,
                      environment=settings.PLAID_ENV,
                      api_version='2019-05-29')





'''
        @csrf_exempt
        def Test(request):
            settings.TEST = request.POST["key"]
            return HttpResponse(settings.TEST)
'''


class AboutPageView(TemplateView):
    template_name = 'about.html'


class HomePageView(TemplateView):
    template_name = 'home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['plaid_environment'] = settings.PLAID_ENV
        context['plaid_public_key'] = settings.PLAID_PUBLIC_KEY
        context['plaid_country_codes'] = settings.PLAID_COUNTRY_CODES
        context['plaid_oauth_nonce'] = settings.PLAID_OAUTH_NONCE
        context['plaid_products'] = settings.PLAID_PRODUCTS
        context['plaid_oauth_redirect_uri'] = settings.PLAID_OAUTH_REDIRECT_URI
        return context


class oauthResponse(TemplateView):
    template_name = 'oauth-response.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['plaid_environment'] = settings.PLAID_ENV
        context['plaid_public_key'] = settings.PLAID_PUBLIC_KEY
        context['plaid_country_codes'] = settings.PLAID_COUNTRY_CODES
        context['plaid_oauth_nonce'] = settings.PLAID_OAUTH_NONCE
        context['plaid_products'] = settings.PLAID_PRODUCTS
        return context


@csrf_exempt
def getPublicToken(request):
    if request.method == 'POST':
        public_token = request.POST['public_token']
    try:
        exchange_response = client.Item.public_token.exchange(public_token)
        settings.access_token = exchange_response['access_token']
    except plaid.errors.PlaidError as e:
        print(e)
    print(exchange_response)
    return HttpResponseRedirect(reverse('auth'))


@csrf_exempt
def getAuth(request):
  try:
    auth_response = client.Auth.get(settings.access_token)
  except plaid.errors.PlaidError as e:
    return print({'error': {'display_message': e.display_message, 'error_code': e.code, 'error_type': e.type }})
  pretty_print_response(auth_response)
  return HttpResponseRedirect(reverse('about'))

# Retrieve Transactions for an Item
# https://plaid.com/docs/#transactions
@csrf_exempt
def get_transactions(request):
  # Pull transactions for the last 30 days
  start_date = '{:%Y-%m-%d}'.format(datetime.datetime.now() + datetime.timedelta(-30))
  end_date = '{:%Y-%m-%d}'.format(datetime.datetime.now())
  try:
    transactions_response = client.Transactions.get(settings.access_token, start_date, end_date)
  except plaid.errors.PlaidError as e:
    return print(format_error(e))
  pretty_print_response(transactions_response)
  return HttpResponse({'error': None, 'transactions': transactions_response})

# Retrieve Identity data for an Item
# https://plaid.com/docs/#identity
@csrf_exempt
def get_identity(request):
  try:
    identity_response = client.Identity.get(settings.access_token)
  except plaid.errors.PlaidError as e:
    return print({'error': {'display_message': e.display_message, 'error_code': e.code, 'error_type': e.type } })
  pretty_print_response(identity_response)
  return HttpResponse({'error': None, 'identity': identity_response})

# Retrieve real-time balance data for each of an Item's accounts
# https://plaid.com/docs/#balance
@csrf_exempt
def get_balance(request):
  try:
    balance_response = client.Accounts.balance.get(settings.access_token)
  except plaid.errors.PlaidError as e:
    return print({'error': {'display_message': e.display_message, 'error_code': e.code, 'error_type': e.type } })
  pretty_print_response(balance_response)
  return HttpResponse({'error': None, 'balance': balance_response})

# Retrieve an Item's accounts
# https://plaid.com/docs/#accounts
@csrf_exempt
def get_accounts(request):
  try:
    accounts_response = client.Accounts.get(settings.access_token)
  except plaid.errors.PlaidError as e:
    return print({'error': {'display_message': e.display_message, 'error_code': e.code, 'error_type': e.type } })
  pretty_print_response(accounts_response)
  return HttpResponse({'error': None, 'accounts': accounts_response})

# Create and then retrieve an Asset Report for one or more Items. Note that an
# Asset Report can contain up to 100 items, but for simplicity we're only
# including one Item here.
# https://plaid.com/docs/#assets
@csrf_exempt
def get_assets(request):
  try:
    asset_report_create_response = client.AssetReport.create([settings.access_token], 10)
  except plaid.errors.PlaidError as e:
    return print({'error': {'display_message': e.display_message, 'error_code': e.code, 'error_type': e.type } })
  pretty_print_response(asset_report_create_response)

  asset_report_token = asset_report_create_response['asset_report_token']

  # Poll for the completion of the Asset Report.
  num_retries_remaining = 20
  asset_report_json = None
  while num_retries_remaining > 0:
    try:
      asset_report_get_response = client.AssetReport.get(asset_report_token)
      asset_report_json = asset_report_get_response['report']
      break
    except plaid.errors.PlaidError as e:
      if e.code == 'PRODUCT_NOT_READY':
        num_retries_remaining -= 1
        time.sleep(1)
        continue
      return HttpResponse({'error': {'display_message': e.display_message, 'error_code': e.code, 'error_type': e.type } })

  if asset_report_json == None:
    return HttpResponse({'error': {'display_message': 'Timed out when polling for Asset Report', 'error_code': e.code, 'error_type': e.type } })

  asset_report_pdf = None
  try:
    asset_report_pdf = client.AssetReport.get_pdf(asset_report_token)
  except plaid.errors.PlaidError as e:
    return print({'error': {'display_message': e.display_message, 'error_code': e.code, 'error_type': e.type } })

  return HttpResponse({
    'error': None,
    'json': asset_report_json,
    'pdf': base64.b64encode(asset_report_pdf),
  })

# Retrieve investment holdings data for an Item
# https://plaid.com/docs/#investments
@csrf_exempt
def get_holdings(request):
  try:
    holdings_response = client.Holdings.get(settings.access_token)
  except plaid.errors.PlaidError as e:
    return print({'error': {'display_message': e.display_message, 'error_code': e.code, 'error_type': e.type } })
  pretty_print_response(holdings_response)
  return HttpResponse({'error': None, 'holdings': holdings_response})

# Retrieve Investment Transactions for an Item
# https://plaid.com/docs/#investments
@csrf_exempt
def get_investment_transactions(request):
  # Pull transactions for the last 30 days
  start_date = '{:%Y-%m-%d}'.format(datetime.datetime.now() + datetime.timedelta(-30))
  end_date = '{:%Y-%m-%d}'.format(datetime.datetime.now())
  try:
    investment_transactions_response = client.InvestmentTransactions.get(settings.access_token,
                                                                         start_date,
                                                                         end_date)
  except plaid.errors.PlaidError as e:
    return print(format_error(e))
  pretty_print_response(investment_transactions_response)
  return HttpResponse({'error': None, 'investment_transactions': investment_transactions_response})

# This functionality is only relevant for the UK Payment Initiation product.
# Retrieve Payment for a specified Payment ID
@csrf_exempt
def payment(request):
  global payment_id
  payment_get_response = client.PaymentInitiation.get_payment(payment_id)
  pretty_print_response(payment_get_response)
  return HttpResponse({'error': None, 'payment': payment_get_response})

# Retrieve high-level information about an Item
# https://plaid.com/docs/#retrieve-item
@csrf_exempt
def item(request):
  item_response = client.Item.get(settings.access_token)
  institution_response = client.Institutions.get_by_id(item_response['item']['institution_id'])
  pretty_print_response(item_response)
  pretty_print_response(institution_response)
  return HttpResponse({'error': None, 'item': item_response['item'], 'institution': institution_response['institution']})
'''
@app.route('/set_access_token', methods=['POST'])
def set_access_token():
  settings.access_token = request.form['access_token'] #sort this out
  item = client.Item.get(settings.access_token)
  return HttpResponse({'error': None, 'item_id': item['item']['item_id']})
'''
# This functionality is only relevant for the UK Payment Initiation product.
# Sets the payment token in memory on the server side. We generate a new
# payment token so that the developer is not required to supply one.
# This makes the quickstart easier to use.
@csrf_exempt
def set_payment_token(request):
  try:
    create_recipient_response = client.PaymentInitiation.create_recipient(
      'Harry Potter',
      'GB33BUKB20201555555555',
      {
        'street': ['4 Privet Drive'],
        'city': 'Little Whinging',
        'postal_code': '11111',
        'country': 'GB',
      },
    )
    recipient_id = create_recipient_response['recipient_id']

    create_payment_response = client.PaymentInitiation.create_payment(
      recipient_id,
      'payment_ref',
      {
        'currency': 'GBP',
        'value': 12.34,
      },
    )
    settings.payment_id = create_payment_response['payment_id']

    create_payment_token_response = client.PaymentInitiation.create_payment_token(settings.payment_id)
    settings.payment_token = create_payment_token_response['payment_token']
  except plaid.errors.PlaidError as e:
    return print({'error': {'display_message': e.display_message, 'error_code': e.code, 'error_type': e.type } })

  return HttpResponse({'error': None, 'payment_token': settings.payment_token})

def pretty_print_response(response):
  print(json.dumps(response, indent=2, sort_keys=True))

def format_error(e):
  return {'error': {'display_message': e.display_message, 'error_code': e.code, 'error_type': e.type, 'error_message': e.message } }



# Create your views here.
