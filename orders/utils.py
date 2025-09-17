GOVERNORATE_SHIPPING_COST = {
    "Cairo": 20, "Giza": 25, "Alexandria": 35, "Dakahlia": 30,
    "Red_Sea": 50, "Beheira": 30, "Fayoum": 28, "Gharbia": 30,
    "Ismailia": 40, "Menofia": 28, "Minya": 32, "Qalyubia": 25,
    "New_Valley": 55, "Suez": 45, "Aswan": 60, "Assiut": 50,
    "Beni_Suef": 35, "Port_Said": 40, "Damietta": 40, "Sharkia": 35,
    "South_Sinai": 65, "Kafr_El_Sheikh": 30, "Matrouh": 70,
    "Luxor": 55, "Qena": 50, "North_Sinai": 60, "Sohag": 50,
}

GOVERNORATE_COORDINATES = {
    "Cairo": (30.0444, 31.2357),
    "Giza": (30.0131, 31.2089),
    "Alexandria": (31.2001, 29.9187),
    "Dakahlia": (31.0553, 31.3807),
    "Red_Sea": (27.2579, 33.8116),
    "Beheira": (31.0336, 30.4603),
    "Fayoum": (29.3096, 30.8418),
    "Gharbia": (30.8750, 31.0364),
    "Ismailia": (30.5965, 32.2711),
    "Menofia": (30.4675, 30.9638),
    "Minya": (28.1096, 30.7500),
    "Qalyubia": (30.3210, 31.2100),
    "New_Valley": (25.6904, 30.5561),
    "Suez": (29.9668, 32.5498),
    "Aswan": (24.0889, 32.8998),
    "Assiut": (27.1800, 31.1850),
    "Beni_Suef": (29.0667, 31.0996),
    "Port_Said": (31.2653, 32.3019),
    "Damietta": (31.4167, 31.8133),
    "Sharkia": (30.7821, 31.5666),
    "South_Sinai": (28.5565, 33.8886),
    "Kafr_El_Sheikh": (31.1110, 30.9396),
    "Matrouh": (31.3546, 27.2373),
    "Luxor": (25.6872, 32.6396),
    "Qena": (26.1612, 32.7169),
    "North_Sinai": (30.5910, 33.8010),
    "Sohag": (26.5563, 31.6940),
}


def calculate_shipping(order):
    """
    تحسب سعر الشحن وتحدث إحداثيات الطلب حسب المحافظة
    """
    if not order.governorate:
        order.latitude = None
        order.longitude = None
        return 50

    coords = GOVERNORATE_COORDINATES.get(order.governorate)
    if coords:
        order.latitude, order.longitude = coords
    else:
        order.latitude = None
        order.longitude = None

    return GOVERNORATE_SHIPPING_COST.get(order.governorate, 50)
