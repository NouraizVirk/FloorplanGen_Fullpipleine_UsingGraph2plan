import sys
import os
sys.path.append(r'e:\Projects\FYP\Graph2Plan\Graph2plan\Interface')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'House.settings')
import django
django.setup()
print("Django setup done")
from Houseweb import views
print("Views imported")
