import json
with open('project_items.json', encoding='utf-16le') as f:
    data = json.load(f)
for i in data['items']:
    content = i.get('content', {})
    if content.get('number') in (4, 5):
        print(f"{content.get('number')}:{i['id']}")
