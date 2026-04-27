from django.urls import path, include
from django.http import JsonResponse
import shutil
import os

def cek_npx(request):
    os.environ["PATH"] = "/usr/local/bin:/usr/bin:/bin:" + os.environ.get("PATH", "")
    npx = shutil.which("npx")
    node = shutil.which("node")
    return JsonResponse({
        "npx": npx,
        "node": node,
        "PATH": os.environ.get("PATH", ""),
    })

urlpatterns = [
    path('', include('klasifikasi.urls')),
    path('cek-npx/', cek_npx),
]