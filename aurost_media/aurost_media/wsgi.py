import os
import sys
 
sys.path.append('/home/c/cg67678/aurost/public_html/aurost_media')
sys.path.append('/home/c/cg67678/aurost/myenv/lib/python3.6/site-packages')
os.environ['DJANGO_SETTINGS_MODULE'] = 'aurost_media.settings'
import django
django.setup()
 
from django.core.handlers import wsgi
application = wsgi.WSGIHandler()