import sys, json, urllib.request, urllib.error

data = json.dumps({'case_text': 'Suspected burglary at 23 Baker Street. Multiple eyewitnesses report stolen items and forced entry.'}).encode('utf-8')
req = urllib.request.Request('http://127.0.0.1:8000/api/v1/bedrock/classify', data=data, headers={'Content-Type': 'application/json'})
try:
    resp = urllib.request.urlopen(req)
    print('STATUS', resp.getcode())
    print(resp.read().decode('utf-8'))
except urllib.error.HTTPError as e:
    print('HTTPERROR', e.code)
    try:
        print(e.read().decode('utf-8'))
    except Exception as re:
        print('ERROR READING BODY', re)
except Exception as e:
    print('ERR', e)
