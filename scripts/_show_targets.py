import json
d = json.load(open('/home/nari/scripts/spinorama_JPY/reports/weekly_targets.json'))
print('generated_at', d.get('generated_at'), 'count', d.get('count'))
for it in d['items']:
    print(it.get('id'), '|', it.get('brand'), '|', it.get('model'), '|', it.get('amount_type'),
          '| est=', it.get('cp_tone_est'), '| jpy=', it.get('price_jpy'),
          '| avail=', it.get('availability'), '| vs=', it.get('verification_status'),
          '| score_tone=', it.get('score_tone'))
