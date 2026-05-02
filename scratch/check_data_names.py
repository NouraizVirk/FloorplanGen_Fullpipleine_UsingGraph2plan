import sys
import os
import pickle
sys.path.append(r'e:\Projects\FYP\Graph2Plan\Graph2plan\Interface')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'House.settings')
import django
django.setup()

from Houseweb import views
views.getTestData()
views.getTrainData()

print("First 10 test names:", views.testNameList[:10])
print("First 10 train names:", views.trainNameList[:10])

if "850" in views.testNameList:
    print("850 is in testNameList")
else:
    print("850 is NOT in testNameList")

if "69519" in views.trainNameList:
    print("69519 is in trainNameList")
else:
    print("69519 is NOT in trainNameList")
