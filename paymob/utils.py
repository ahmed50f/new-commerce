# import requests, hmac, hashlib
# from django.http import JsonResponse
# from django.conf import settings

# def generate_paymob_url(amount, currency, items, billing_data, extras=None):
#     url = "https://accept.paymob.com/v1/intention/"

#     headers = {
#         "Authorization": f"Token {settings.PAYMOB_SECRET_KEY}",
#         "Content-Type": "application/json",
#     }

#     body = {
#         "amount": amount,
#         "currency": currency,
#         "payment_methods": [settings.PAYMOB_INTEGRATION_CARD_ID, settings.PAYMOB_INTEGRATION_WALLET_ID, settings.PAYMOB_INTEGRATION_KIOSK_ID],
#         "items": items,
#         "billing_data": billing_data,
#     }

#     if extras:
#         body["extras"] = extras

#     response = requests.post(url, json=body, headers=headers)

#     if response.status_code == 201:
#         data = response.json()
#         client_secret = data.get("client_secret")
#         url = f"https://accept.paymob.com/unifiedcheckout/?publicKey={settings.PAYMOB_PUBLIC_KEY}&clientSecret={client_secret}"
#         return url
#     else:
#         return "error"

# def to_lowercase_boolean(value):
#     if isinstance(value, bool):
#         return str(value).lower()
#     return value

# def generate_hmac_sha512(key, message):
#     if isinstance(key, str):
#         key = key.encode("utf-8")
#     if isinstance(message, str):
#         message = message.encode("utf-8")

#     hmac_obj = hmac.new(key, message, hashlib.sha512)

#     return hmac_obj.hexdigest()

# def get_auth_token(request):
#     url = "https://accept.paymobsolutions.com/api/auth/tokens"

#     headers = {"Content-Type": "application/json"}

#     data = {"api_key": settings.PAYMOB_API_KEY}

#     response = requests.post(url, json=data, headers=headers)

#     if response.status_code == 201:
#         return response.json().get("token")
#     else:
#         return JsonResponse({"status": "failure", "error": "Failed to retrieve authentication token"}, status=500)

# def get_received_hmac(transaction_id, auth_token):
#     url = f"https://accept.paymobsolutions.com/api/acceptance/transactions/{transaction_id}/hmac_calc?token={auth_token}"

#     response = requests.get(url)

#     if response.status_code == 200:
#         return response.json().get("hmac")
#     else:
#         return JsonResponse({"status": "failure", "error": "Failed to retrieve HMAC"}, status=500)

# def get_calculated_hmac(transaction):
#     values_in_order = [
#         transaction.get("amount_cents"),
#         transaction.get("created_at"),
#         transaction.get("currency"),
#         to_lowercase_boolean(transaction.get("error_occured")),
#         to_lowercase_boolean(transaction.get("has_parent_transaction")),
#         transaction.get("id"),
#         transaction.get("integration_id"),
#         to_lowercase_boolean(transaction.get("is_3d_secure")),
#         to_lowercase_boolean(transaction.get("is_auth")),
#         to_lowercase_boolean(transaction.get("is_capture")),
#         to_lowercase_boolean(transaction.get("is_refunded")),
#         to_lowercase_boolean(transaction.get("is_standalone_payment")),
#         to_lowercase_boolean(transaction.get("is_voided")),
#         transaction.get("order").get("id") if transaction.get("order") else None,
#         transaction.get("owner"),
#         to_lowercase_boolean(transaction.get("pending")),
#         (
#             transaction.get("source_data").get("pan")
#             if transaction.get("source_data")
#             else None
#         ),
#         (
#             transaction.get("source_data").get("sub_type")
#             if transaction.get("source_data")
#             else None
#         ),
#         (
#             transaction.get("source_data").get("type")
#             if transaction.get("source_data")
#             else None
#         ),
#         to_lowercase_boolean(transaction.get("success")),
#     ]

#     concatenated_string = "".join(str(value) for value in values_in_order if value is not None)
#     return generate_hmac_sha512(settings.PAYMOB_HMAC, concatenated_string)