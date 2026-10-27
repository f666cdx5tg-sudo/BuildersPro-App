#!/usr/bin/env python3
"""Makes the sample backup files some tests need (made-up data, never real jobs):
web.json (web backup), nat.json (old native app export), big.json (1 job, 181 photos +
3 punch photos), qr.png (a fake QR code). Written beside the tests; git ignores them.
Run: python3 tools/make_test_fixtures.py"""
import json, base64, io, random, os
from PIL import Image, ImageDraw
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def pic(seed, w=900, h=675, q=82):
    random.seed(seed)
    im = Image.effect_noise((w // 6, h // 6), 40).convert('RGB').resize((w, h))
    ImageDraw.Draw(im).text((20, 20), 'test photo %d' % seed, fill=(255, 255, 0))
    b = io.BytesIO(); im.save(b, 'JPEG', quality=q); return 'data:image/jpeg;base64,' + base64.b64encode(b.getvalue()).decode()
A, B = pic(1), pic(2)
T0, T1 = '2026-10-01T10:00:00.000Z', '2026-10-05T10:00:00.000Z'
web = {'app': 'BuildersPro', 'exportedAt': '2026-10-24T12:00:00.000Z', 'exportedBy': 'BuildersPro web backup (test)', 'db': {
  'jobs': [{'id': 'w1', 'name': 'N. Peach St', 'client': 'Shelden Washington', 'address': '1536 N. Peach St', 'city': 'Philadelphia', 'state': 'PA', 'zip': '19131', 'clientEmail': 'sw@x.com', 'clientPhone': '8626869866', 'status': 'Active', 'updatedAt': T0},
           {'id': 'w2', 'name': 'Shedwick', 'client': 'Courtney Benson', 'address': '634 N. Shedwick St', 'updatedAt': T0},
           {'id': 'w3', 'name': 'Web Only Job', 'client': 'Pat Web', 'updatedAt': T0}],
  'rooms': [{'id': 'r1', 'jobId': 'w1', 'name': 'Stairs', 'updatedAt': T0}, {'id': 'r2', 'jobId': 'w1', 'name': 'Bath', 'updatedAt': T0}],
  'punchlist': [{'id': 'p1', 'jobId': 'w1', 'roomId': 'r1', 'text': 'Install handrail', 'done': False, 'updatedAt': T0},
                {'id': 'pw', 'jobId': 'w1', 'roomId': 'r2', 'text': 'Web only item', 'done': False, 'updatedAt': T0}],
  'photos': [{'id': 'ph1', 'jobId': 'w1', 'roomId': 'r1', 'src': A, 'date': T0, 'updatedAt': T0}],
  'appointments': [{'id': 'a1', 'jobId': 'w1', 'date': '2026-10-28', 'time': '09:30', 'title': 'Rough inspection', 'updatedAt': T0}],
  'contacts': [], 'nextId': 500}}
nat = {'app': 'BuildersPro', 'exportedAt': '2026-10-24T12:05:00.000Z', 'exportedBy': 'BuildersPro native export (test)', 'db': {
  'jobs': [{'id': 'nxj_w1', 'name': 'N. Peach St', 'client': 'Shelden Washington', 'address': '1536 N. Peach St', 'city': '', 'state': '', 'zip': '', 'clientEmail': '', 'status': 'Active', 'updatedAt': T1},
           {'id': 'nxj_9f2a', 'name': 'Shedwick', 'client': 'Courtney Benson', 'address': '634 N. Shedwick St', 'updatedAt': T1}],
  'rooms': [{'id': 'nxr_AAA', 'jobId': 'nxj_w1', 'name': 'Stairs', 'updatedAt': T1}, {'id': 'nxr_BBB', 'jobId': 'nxj_w1', 'name': 'Kitchen', 'updatedAt': T1}],
  'punchlist': [{'id': 'nxp_1', 'jobId': 'nxj_w1', 'roomId': 'nxr_AAA', 'text': 'Install handrail', 'done': True, 'updatedAt': T1},
                {'id': 'nxp_2', 'jobId': 'nxj_w1', 'roomId': 'nxr_BBB', 'text': 'Native only item', 'done': False, 'updatedAt': T1}],
  'photos': [{'id': 'nxph_1', 'jobId': 'nxj_w1', 'roomId': 'nxr_AAA', 'src': A, 'date': T1, 'updatedAt': T1}, {'id': 'nxph_2', 'jobId': 'nxj_w1', 'roomId': 'nxr_BBB', 'src': B, 'date': T1, 'updatedAt': T1}],
  'appointments': [{'id': 'nxa_a1', 'jobId': 'nxj_w1', 'date': '2026-10-28', 'time': '09:30', 'title': 'Rough inspection', 'updatedAt': T1}],
  'contacts': [{'id': 'nxb_1', 'type': 'Contractor', 'name': 'Joe Tile', 'company': 'Joe Tile LLC', 'phone': '2015550111', 'updatedAt': T1}]}}
big = {'app': 'BuildersPro', 'exportedAt': T1, 'exportedBy': 'BuildersPro big backup (test)', 'db': {
  'jobs': [{'id': 'bj1', 'name': 'Big Job One', 'client': 'A'}],
  'punchlist': [{'id': 'bpu1', 'jobId': 'bj1', 'text': 'Item one', 'done': False, 'photosBefore': [{'src': pic(900), 'date': T0}], 'photosAfter': [], 'updatedAt': T0},
                {'id': 'bpu2', 'jobId': 'bj1', 'text': 'Item two', 'done': False, 'photosBefore': [{'src': pic(901), 'date': T0}, {'src': pic(902), 'date': T0}], 'photosAfter': [], 'updatedAt': T0}],
  'photos': [{'id': 'bp%d' % i, 'jobId': 'bj1', 'src': pic(100 + i, 800, 600, 75), 'date': T0, 'updatedAt': T0} for i in range(181)], 'nextId': 1000}}
for name, obj in (('web.json', web), ('nat.json', nat), ('big.json', big)):
    json.dump(obj, open(os.path.join(ROOT, name), 'w'))
im = Image.new('RGB', (400, 400), 'white'); d = ImageDraw.Draw(im)
for x in range(0, 400, 40):
    for y in range(0, 400, 40):
        if (x * 7 + y * 3) % 3 == 0: d.rectangle([x, y, x + 38, y + 38], fill='black')
im.save(os.path.join(ROOT, 'qr.png'))
print('test fixtures written: web.json nat.json big.json qr.png')
