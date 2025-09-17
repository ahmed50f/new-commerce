# import json
# from django.http import JsonResponse
# from django.shortcuts import redirect
# from rest_framework.decorators import api_view, permission_classes
# from rest_framework.permissions import AllowAny
# from django.shortcuts import redirect
# from django.views.decorators.csrf import csrf_exempt
# from .utils import *

# @api_view(["GET"])
# @permission_classes((AllowAny,))
# def paymob_initialize(order=None, currency="EGP"):
#     # you can pass extras if you need
#     order = {
#         "amount": 50000,
#         "items": [
#             {
#                 "name": "Item 1",
#                 "amount": 20000,
#                 "description": "First item",
#                 "quantity": 1,
#             },
#             {
#                 "name": "Item 2",
#                 "amount": 30000,
#                 "description": "Second item",
#                 "quantity": 1,
#             },
#         ],
#         "billing_data": {
#             "apartment": "123",
#             "first_name": "John",
#             "last_name": "Doe",
#             "street": "Sample Street",
#             "building": "10",
#             "phone_number": "+201018181818",
#             "city": "Cairo",
#             "country": "EG",
#             "email": "john.doe@example.com",
#             "floor": "3",
#             "state": "Cairo",
#         },
#     }

#     paymob_iframe_url = generate_paymob_url(order["amount"], currency, order["items"], order["billing_data"])

#     if paymob_iframe_url == "error":
#         return JsonResponse({"error": "Failed to get client secret"})
#     else:
#         return redirect(paymob_iframe_url)

# @api_view(["POST"])
# @csrf_exempt
# @permission_classes((AllowAny,))
# def paymob_webhook_processed(request):
#     data = json.loads(request.body.decode("utf-8"))
#     received_hmac = get_received_hmac(data.get("transaction").get("id"), get_auth_token(request))
#     calculated_hmac = get_calculated_hmac(data.get("transaction"))
#     if received_hmac == calculated_hmac:
#         return JsonResponse({"status": "success"})
#     else:
#         return JsonResponse({"status": "failure", "error": "Invalid HMAC"}, status=400)

# @api_view(["GET"])
# @permission_classes((AllowAny,))
# def paymob_webhook_response(request):
#     success = request.GET.get("success")
#     if success == "true":
#         return redirect("https://shawarma.cyparta.com/success")
#     else:
#         return redirect("https://shawarma.cyparta.com/failed")