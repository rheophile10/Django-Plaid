from django.urls import path
from . import views as v

urlpatterns = [
    path('', v.HomePageView.as_view(), name='home'),
    path('about/', v.AboutPageView.as_view(), name='about'),
    path('get_access_token/', v.getPublicToken, name='access'),
    path('oauth-response/', v.oauthResponse.as_view(),
        name='oauthresponse'),
    path('auth/', v.getAuth, name='auth'),
    path('transactions/', v.get_transactions, name='transactions'),
    path('identity/', v.get_identity, name='identity'),
    path('balance/', v.get_balance, name='balance'),
    path('accounts/', v.get_accounts, name='accounts'),
    path('assets/', v.get_assets, name='assets'),
    path('holdings/', v.get_holdings, name='holdings'),
    path('investment_transactions/', v.get_investment_transactions, name='investment_transactions'),
    path('payment/', v.payment, name='payment'),
    path('item/', v.item, name='item'),
    path('set_payment_token/', v.set_payment_token, name='set_payment_token')
    #path('test/', v.Test, name='test')
]