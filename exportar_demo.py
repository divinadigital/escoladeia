"""
Gera assets/demo-db.js: os dados de demonstração usados pela versão estática (GitHub Pages),
onde não existe server.py. Rode depois de mudar o seed.py:

    python exportar_demo.py
"""
import json, os, sqlite3, sys, tempfile, time

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
import server, seed  # noqa: E402

tmp = os.path.join(tempfile.mkdtemp(), 'demo.db')
server.DB = tmp
server.criar_banco()

c = sqlite3.connect(tmp)
c.row_factory = sqlite3.Row
db = {'gerado': int(time.time())}
for t in ('usuarios', 'cursos', 'matriculas', 'progresso', 'cliques', 'avaliacoes'):
    db[t] = [dict(r) for r in c.execute('SELECT * FROM %s' % t)]
for cur in db['cursos']:
    for k in ('modulos', 'aprender', 'requisitos'):
        cur[k] = json.loads(cur[k] or '[]')
c.close()

saida = os.path.join(ROOT, 'assets', 'demo-db.js')
with open(saida, 'w', encoding='utf-8') as f:
    f.write('/* Gerado por exportar_demo.py. Não edite à mão. */\nwindow.EIA_DEMO_DB = ')
    json.dump(db, f, ensure_ascii=False, separators=(',', ':'))
    f.write(';\n')
print('ok:', saida, os.path.getsize(saida) // 1024, 'KB')
