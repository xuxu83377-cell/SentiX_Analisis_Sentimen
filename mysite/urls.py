from django.urls import path, include
from django.http import JsonResponse
import shutil
import os
import subprocess

def cek_npx(request):
    os.environ["PATH"] = "/usr/local/bin:/usr/bin:/bin:" + os.environ.get("PATH", "")
    
    node_ver = subprocess.run(["node", "--version"], capture_output=True, text=True)
    npm_ver = subprocess.run(["npm", "--version"], capture_output=True, text=True)
    th_exists = os.path.exists("/usr/local/bin/tweet-harvest")
    th_ver = subprocess.run(["tweet-harvest", "--version"], capture_output=True, text=True)
    
    return JsonResponse({
        "node_version": node_ver.stdout.strip(),
        "npm_version": npm_ver.stdout.strip(),
        "tweet_harvest_exists": th_exists,
        "tweet_harvest_version": th_ver.stdout.strip(),
        "tweet_harvest_error": th_ver.stderr.strip()[:300],
    })

urlpatterns = [
    path('', include('klasifikasi.urls')),
    path('cek-npx/', cek_npx),
]