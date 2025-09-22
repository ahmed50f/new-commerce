
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls.i18n import i18n_patterns

urlpatterns = [
    path('i18n/', include('django.conf.urls.i18n')),
     
]

urlpatterns += i18n_patterns(
   path('admin/', admin.site.urls),
    #path('', include('paymob.urls')),
    path('api/accounts/', include('accounts.urls')),  
    path('api/products/', include('products.urls')),
    path('api/orders/', include('orders.urls')),

)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)