"""
Servidor da Escola de IA.

Serve o site e responde à API em /api/... usando um banco SQLite (dados/escola.db).
Não precisa instalar nada além do Python 3.9+.

Uso:
    python server.py            -> http://localhost:5530
    python server.py 8080       -> outra porta

Contas de demonstração: veja LEIA-ME.md.
"""
import hashlib, json, os, re, secrets, sqlite3, sys, time, unicodedata
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

ROOT = os.path.dirname(os.path.abspath(__file__))
DADOS = os.path.join(ROOT, 'dados')
DB = os.path.join(DADOS, 'escola.db')
SESSAO_VIDA = 7 * 24 * 3600
COMISSAO_AFILIADO = 0.30          # 30% para quem indicou
REPASSE_CRIADOR = 0.70            # 70% para o parceiro que criou o curso
PAPEIS = ('aluno', 'professor', 'parceiro', 'admin')
BLOQUEADOS = ('/dados', '/server.py', '/seed.py', '/.')
TENTATIVAS = {}                   # ip -> [timestamps de erro]


# ---------------------------------------------------------------- banco
def conectar():
    c = sqlite3.connect(DB, timeout=10)
    c.row_factory = sqlite3.Row
    c.execute('PRAGMA foreign_keys = ON')
    return c


def criar_banco():
    os.makedirs(DADOS, exist_ok=True)
    novo = not os.path.exists(DB)
    with conectar() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY, nome TEXT NOT NULL, email TEXT NOT NULL,
            papel TEXT NOT NULL, sal TEXT NOT NULL, hash TEXT NOT NULL,
            bio TEXT DEFAULT '', ref TEXT UNIQUE, parceiro_tipo TEXT DEFAULT '',
            criado INTEGER NOT NULL, UNIQUE(email, papel));
        CREATE TABLE IF NOT EXISTS sessoes (
            token TEXT PRIMARY KEY, usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
            expira INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS cursos (
            id INTEGER PRIMARY KEY, autor_id INTEGER NOT NULL REFERENCES usuarios(id),
            slug TEXT UNIQUE NOT NULL, titulo TEXT NOT NULL, resumo TEXT DEFAULT '',
            descricao TEXT DEFAULT '', categoria TEXT DEFAULT 'Fundamentos', nivel TEXT DEFAULT 'Iniciante',
            preco REAL DEFAULT 0, cor TEXT DEFAULT 'lima', status TEXT DEFAULT 'rascunho',
            motivo TEXT DEFAULT '', modulos TEXT DEFAULT '[]', criado INTEGER NOT NULL, atualizado INTEGER NOT NULL,
            aprender TEXT DEFAULT '[]', requisitos TEXT DEFAULT '[]', preco_original REAL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS matriculas (
            id INTEGER PRIMARY KEY, usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
            curso_id INTEGER NOT NULL REFERENCES cursos(id) ON DELETE CASCADE,
            ref_id INTEGER, valor REAL DEFAULT 0, criado INTEGER NOT NULL, UNIQUE(usuario_id, curso_id));
        CREATE TABLE IF NOT EXISTS progresso (
            usuario_id INTEGER NOT NULL, curso_id INTEGER NOT NULL, aula_id TEXT NOT NULL,
            criado INTEGER NOT NULL, PRIMARY KEY(usuario_id, curso_id, aula_id));
        CREATE TABLE IF NOT EXISTS cliques (ref TEXT NOT NULL, curso_id INTEGER, criado INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS avaliacoes (
            usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
            curso_id INTEGER NOT NULL REFERENCES cursos(id) ON DELETE CASCADE,
            nota INTEGER NOT NULL, texto TEXT DEFAULT '', criado INTEGER NOT NULL, PRIMARY KEY(usuario_id, curso_id));
        ''')
        # bancos criados antes destas colunas existirem
        cols = {r[1] for r in c.execute('PRAGMA table_info(cursos)')}
        for col, tipo in (('aprender', "TEXT DEFAULT '[]'"), ('requisitos', "TEXT DEFAULT '[]'"), ('preco_original', 'REAL DEFAULT 0')):
            if col not in cols:
                c.execute('ALTER TABLE cursos ADD COLUMN %s %s' % (col, tipo))
    if novo:
        import seed
        seed.popular(DB, hash_senha)
        print('Banco criado com dados de demonstração.')


def hash_senha(senha, sal=None):
    sal = sal or secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac('sha256', senha.encode('utf-8'), bytes.fromhex(sal), 120_000).hex()
    return sal, h


def slugify(t):
    t = unicodedata.normalize('NFKD', t).encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-z0-9]+', '-', t.lower()).strip('-')[:60] or 'curso'


def lista(v):
    if isinstance(v, str):
        v = v.split('\n')
    return [str(x).strip()[:200] for x in (v or []) if str(x).strip()][:12]


def num(v):
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def contar_aulas(modulos):
    return sum(len(m.get('aulas', [])) for m in modulos)


def duracao_total(modulos):
    return sum(int(a.get('min') or 0) for m in modulos for a in m.get('aulas', []))


def selo(alunos, nota, n_aval, criado):
    if alunos >= 30:
        return 'Mais vendido'
    if n_aval >= 4 and nota >= 4.7:
        return 'Mais bem avaliado'
    if time.time() - criado < 21 * 86400:
        return 'Novo'
    return ''


def curso_publico(row, c, detalhado=False, liberado=False):
    mods = json.loads(row['modulos'] or '[]')
    autor = c.execute('SELECT id, nome, bio, papel FROM usuarios WHERE id=?', (row['autor_id'],)).fetchone()
    alunos = c.execute('SELECT COUNT(*) FROM matriculas WHERE curso_id=?', (row['id'],)).fetchone()[0]
    media, n_aval = c.execute('SELECT COALESCE(AVG(nota),0), COUNT(*) FROM avaliacoes WHERE curso_id=?', (row['id'],)).fetchone()
    d = {
        'id': row['id'], 'slug': row['slug'], 'titulo': row['titulo'], 'resumo': row['resumo'],
        'categoria': row['categoria'], 'nivel': row['nivel'], 'preco': row['preco'], 'cor': row['cor'],
        'preco_original': row['preco_original'] or 0, 'nota': round(media, 1), 'avaliacoes': n_aval,
        'selo': selo(alunos, round(media, 1), n_aval, row['criado']), 'aprender': json.loads(row['aprender'] or '[]')[:3],
        'status': row['status'], 'aulas': contar_aulas(mods), 'minutos': duracao_total(mods), 'alunos': alunos,
        'atualizado': row['atualizado'],
        'autor': {'id': autor['id'], 'nome': autor['nome'], 'bio': autor['bio'],
                  'selo': 'Professor da casa' if autor['papel'] == 'professor' else 'Parceiro criador'},
    }
    if detalhado:
        d['descricao'] = row['descricao']
        d['aprender'] = json.loads(row['aprender'] or '[]')
        d['requisitos'] = json.loads(row['requisitos'] or '[]')
        ids = [x[0] for x in c.execute("SELECT id FROM cursos WHERE autor_id=? AND status='publicado'", (autor['id'],))]
        q = ','.join('?' * len(ids)) or 'NULL'
        a_media, a_n = c.execute('SELECT COALESCE(AVG(nota),0), COUNT(*) FROM avaliacoes WHERE curso_id IN (%s)' % q, ids).fetchone()
        d['autor'].update({'cursos': len(ids), 'nota': round(a_media, 1), 'avaliacoes': a_n,
                           'alunos': c.execute('SELECT COUNT(DISTINCT usuario_id) FROM matriculas WHERE curso_id IN (%s)' % q, ids).fetchone()[0]})
        d['distribuicao'] = {str(k): 0 for k in range(1, 6)}
        for nota, n in c.execute('SELECT nota, COUNT(*) FROM avaliacoes WHERE curso_id=? GROUP BY nota', (row['id'],)):
            d['distribuicao'][str(nota)] = n
        d['comentarios'] = [{'nome': x['nome'], 'nota': x['nota'], 'texto': x['texto'], 'criado': x['criado']} for x in c.execute(
            '''SELECT u.nome, a.nota, a.texto, a.criado FROM avaliacoes a JOIN usuarios u ON u.id=a.usuario_id
               WHERE a.curso_id=? AND a.texto<>'' ORDER BY a.criado DESC LIMIT 12''', (row['id'],))]
        d['modulos'] = [{
            'titulo': m.get('titulo', ''),
            'aulas': [{
                'id': a['id'], 'titulo': a.get('titulo', ''), 'min': a.get('min', 0),
                'gratis': bool(a.get('gratis')), 'tipo': 'video' if a.get('video') else 'texto',
                'bloqueada': not (liberado or a.get('gratis')),
            } for a in m.get('aulas', [])]
        } for m in mods]
    return d


# ---------------------------------------------------------------- servidor
class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=ROOT, **kw)

    def log_message(self, fmt, *args):
        if '/api/' in str(args[0] if args else ''):
            sys.stderr.write('%s %s\n' % (self.log_date_time_string(), fmt % args))

    def end_headers(self):
        self.send_header('X-Content-Type-Options', 'nosniff')
        if not self.path.startswith('/api/'):
            self.send_header('Cache-Control', 'no-cache')
        super().end_headers()

    # --- respostas
    def json(self, dados, status=200, cookie=None):
        corpo = json.dumps(dados, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(corpo)))
        self.send_header('Cache-Control', 'no-store')
        if cookie is not None:
            self.send_header('Set-Cookie', cookie)
        self.end_headers()
        self.wfile.write(corpo)

    def erro(self, msg, status=400):
        self.json({'erro': msg}, status)

    def corpo(self):
        n = int(self.headers.get('Content-Length') or 0)
        if n > 2_000_000:
            return {}
        try:
            return json.loads(self.rfile.read(n) or b'{}')
        except ValueError:
            return {}

    def token(self):
        for parte in (self.headers.get('Cookie') or '').split(';'):
            k, _, v = parte.strip().partition('=')
            if k == 'eia_sessao':
                return v
        return None

    def usuario(self, c):
        t = self.token()
        if not t:
            return None
        r = c.execute('''SELECT u.* FROM sessoes s JOIN usuarios u ON u.id=s.usuario_id
                         WHERE s.token=? AND s.expira>?''', (t, int(time.time()))).fetchone()
        return r

    # --- roteamento
    def do_GET(self):
        p = urlparse(self.path)
        if any(p.path.startswith(b) for b in BLOQUEADOS):
            self.send_error(404)
            return
        if p.path.startswith('/api/'):
            return self.api('GET', p.path[5:], {k: v[0] for k, v in parse_qs(p.query).items()})
        return super().do_GET()

    def do_POST(self):
        p = urlparse(self.path)
        if not p.path.startswith('/api/'):
            self.send_error(405)
            return
        return self.api('POST', p.path[5:], self.corpo())

    def api(self, metodo, rota, dados):
        fn = getattr(self, 'r_' + rota.replace('/', '_').replace('-', '_'), None)
        if not fn:
            return self.erro('Rota não encontrada.', 404)
        try:
            with conectar() as c:
                return fn(c, dados, metodo)
        except Exception as e:  # noqa
            import traceback; traceback.print_exc()
            return self.erro('Erro interno: %s' % e, 500)

    # exige login com um dos papéis
    def exigir(self, c, *papeis):
        u = self.usuario(c)
        if not u:
            self.erro('Faça login para continuar.', 401)
            return None
        if papeis and u['papel'] not in papeis:
            self.erro('Esta área é de outro tipo de conta.', 403)
            return None
        return u

    # ------------------------------------------------ autenticação
    def r_cadastro(self, c, d, m):
        nome = (d.get('nome') or '').strip()
        email = (d.get('email') or '').strip().lower()
        senha = d.get('senha') or ''
        papel = d.get('papel')
        if papel not in ('aluno', 'professor', 'parceiro'):
            return self.erro('Tipo de conta inválido.')
        if len(nome) < 2:
            return self.erro('Informe seu nome.')
        if not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email):
            return self.erro('E-mail inválido.')
        if len(senha) < 6:
            return self.erro('A senha precisa ter pelo menos 6 caracteres.')
        if c.execute('SELECT 1 FROM usuarios WHERE email=? AND papel=?', (email, papel)).fetchone():
            return self.erro('Já existe uma conta de %s com este e-mail.' % papel)
        sal, h = hash_senha(senha)
        ref = None
        tipo = ''
        if papel == 'parceiro':
            tipo = d.get('parceiro_tipo') if d.get('parceiro_tipo') in ('afiliado', 'criador', 'ambos') else 'ambos'
            ref = slugify(nome.split()[0])[:10] + secrets.token_hex(2)
        cur = c.execute('INSERT INTO usuarios (nome,email,papel,sal,hash,ref,parceiro_tipo,criado) VALUES (?,?,?,?,?,?,?,?)',
                        (nome, email, papel, sal, h, ref, tipo, int(time.time())))
        return self.iniciar_sessao(c, cur.lastrowid)

    def r_login(self, c, d, m):
        ip = self.client_address[0]
        agora = time.time()
        TENTATIVAS[ip] = [t for t in TENTATIVAS.get(ip, []) if agora - t < 600]
        if len(TENTATIVAS[ip]) >= 8:
            return self.erro('Muitas tentativas. Aguarde alguns minutos.', 429)
        email = (d.get('email') or '').strip().lower()
        papel = d.get('papel')
        u = c.execute('SELECT * FROM usuarios WHERE email=? AND papel=?', (email, papel)).fetchone()
        if not u or hash_senha(d.get('senha') or '', u['sal'])[1] != u['hash']:
            TENTATIVAS[ip].append(agora)
            outro = c.execute('SELECT papel FROM usuarios WHERE email=? AND papel<>?', (email, papel)).fetchone()
            if outro and not u:
                return self.erro('Este e-mail é de uma conta de %s. Troque a aba acima.' % outro['papel'], 401)
            return self.erro('E-mail ou senha incorretos.', 401)
        return self.iniciar_sessao(c, u['id'])

    def iniciar_sessao(self, c, uid):
        t = secrets.token_urlsafe(32)
        c.execute('DELETE FROM sessoes WHERE expira<?', (int(time.time()),))
        c.execute('INSERT INTO sessoes VALUES (?,?,?)', (t, uid, int(time.time()) + SESSAO_VIDA))
        u = c.execute('SELECT * FROM usuarios WHERE id=?', (uid,)).fetchone()
        cookie = 'eia_sessao=%s; Path=/; Max-Age=%d; HttpOnly; SameSite=Lax' % (t, SESSAO_VIDA)
        return self.json({'usuario': self.perfil(u)}, cookie=cookie)

    def perfil(self, u):
        return {'id': u['id'], 'nome': u['nome'], 'email': u['email'], 'papel': u['papel'],
                'ref': u['ref'], 'parceiro_tipo': u['parceiro_tipo'], 'bio': u['bio']}

    def r_eu(self, c, d, m):
        u = self.usuario(c)
        return self.json({'usuario': self.perfil(u) if u else None})

    def r_sair(self, c, d, m):
        t = self.token()
        if t:
            c.execute('DELETE FROM sessoes WHERE token=?', (t,))
        return self.json({'ok': True}, cookie='eia_sessao=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax')

    def r_perfil(self, c, d, m):
        u = self.exigir(c)
        if not u:
            return
        if m == 'POST':
            nome = (d.get('nome') or u['nome']).strip()[:80]
            bio = (d.get('bio') or '').strip()[:400]
            c.execute('UPDATE usuarios SET nome=?, bio=? WHERE id=?', (nome, bio, u['id']))
            u = c.execute('SELECT * FROM usuarios WHERE id=?', (u['id'],)).fetchone()
        return self.json({'usuario': self.perfil(u)})

    # ------------------------------------------------ catálogo
    def r_cursos(self, c, d, m):
        rows = c.execute("SELECT * FROM cursos WHERE status='publicado' ORDER BY id").fetchall()
        cursos = [curso_publico(r, c) for r in rows]
        stats = {
            'cursos': len(cursos),
            'aulas': sum(x['aulas'] for x in cursos),
            'alunos': c.execute("SELECT COUNT(*) FROM usuarios WHERE papel='aluno'").fetchone()[0],
            'criadores': c.execute("SELECT COUNT(DISTINCT autor_id) FROM cursos WHERE status='publicado'").fetchone()[0],
        }
        return self.json({'cursos': cursos, 'stats': stats})

    def r_curso(self, c, d, m):
        r = c.execute('SELECT * FROM cursos WHERE slug=? OR id=?', (d.get('slug', ''), d.get('id', -1))).fetchone()
        if not r:
            return self.erro('Curso não encontrado.', 404)
        u = self.usuario(c)
        dono = u and (u['id'] == r['autor_id'] or u['papel'] == 'admin')
        if r['status'] != 'publicado' and not dono:
            return self.erro('Curso não encontrado.', 404)
        matriculado = bool(u and c.execute('SELECT 1 FROM matriculas WHERE usuario_id=? AND curso_id=?', (u['id'], r['id'])).fetchone())
        curso = curso_publico(r, c, detalhado=True, liberado=matriculado or dono)
        feitas = []
        if u:
            feitas = [x[0] for x in c.execute('SELECT aula_id FROM progresso WHERE usuario_id=? AND curso_id=?', (u['id'], r['id']))]
        minha = None
        if u:
            x = c.execute('SELECT nota, texto FROM avaliacoes WHERE usuario_id=? AND curso_id=?', (u['id'], r['id'])).fetchone()
            minha = dict(x) if x else None
        return self.json({'curso': curso, 'matriculado': matriculado, 'feitas': feitas, 'minha_avaliacao': minha})

    def r_avaliar(self, c, d, m):
        u = self.exigir(c, 'aluno')
        if not u:
            return
        r = c.execute('SELECT id FROM cursos WHERE id=?', (d.get('curso_id'),)).fetchone()
        if not r or not c.execute('SELECT 1 FROM matriculas WHERE usuario_id=? AND curso_id=?', (u['id'], r['id'])).fetchone():
            return self.erro('Só quem está matriculado pode avaliar o curso.', 403)
        try:
            nota = int(d.get('nota'))
        except (TypeError, ValueError):
            nota = 0
        if not 1 <= nota <= 5:
            return self.erro('Escolha de 1 a 5 estrelas.')
        c.execute('INSERT OR REPLACE INTO avaliacoes VALUES (?,?,?,?,?)',
                  (u['id'], r['id'], nota, (d.get('texto') or '').strip()[:1200], int(time.time())))
        return self.json({'ok': True})

    def r_clique(self, c, d, m):
        ref = (d.get('ref') or '')[:20]
        if ref and c.execute('SELECT 1 FROM usuarios WHERE ref=?', (ref,)).fetchone():
            c.execute('INSERT INTO cliques VALUES (?,?,?)', (ref, d.get('curso_id'), int(time.time())))
        return self.json({'ok': True})

    def r_matricular(self, c, d, m):
        u = self.exigir(c, 'aluno')
        if not u:
            return
        ids = d.get('curso_ids') or [d.get('curso_id')]
        ref = c.execute("SELECT id FROM usuarios WHERE ref=? AND papel='parceiro'", ((d.get('ref') or '')[:20],)).fetchone()
        feitos = []
        for cid in ids[:50]:
            r = c.execute("SELECT * FROM cursos WHERE id=? AND status='publicado'", (cid,)).fetchone()
            if not r:
                continue
            ref_id = ref['id'] if ref and ref['id'] != r['autor_id'] else None
            c.execute('INSERT OR IGNORE INTO matriculas (usuario_id,curso_id,ref_id,valor,criado) VALUES (?,?,?,?,?)',
                      (u['id'], r['id'], ref_id, r['preco'], int(time.time())))
            feitos.append(r['slug'])
        if not feitos:
            return self.erro('Curso indisponível.', 404)
        return self.json({'ok': True, 'slug': feitos[0], 'slugs': feitos})

    def r_aula(self, c, d, m):
        u = self.usuario(c)
        r = c.execute('SELECT * FROM cursos WHERE slug=?', (d.get('curso', ''),)).fetchone()
        if not r:
            return self.erro('Curso não encontrado.', 404)
        mods = json.loads(r['modulos'] or '[]')
        aula = next((a for mm in mods for a in mm.get('aulas', []) if a['id'] == d.get('aula')), None)
        if not aula:
            return self.erro('Aula não encontrada.', 404)
        liberado = bool(aula.get('gratis'))
        if u:
            liberado = liberado or u['id'] == r['autor_id'] or u['papel'] == 'admin' or bool(
                c.execute('SELECT 1 FROM matriculas WHERE usuario_id=? AND curso_id=?', (u['id'], r['id'])).fetchone())
        if not liberado:
            return self.erro('Matricule-se para assistir a esta aula.', 403)
        return self.json({'aula': aula})

    def r_concluir(self, c, d, m):
        u = self.exigir(c, 'aluno')
        if not u:
            return
        r = c.execute('SELECT id, modulos FROM cursos WHERE slug=?', (d.get('curso', ''),)).fetchone()
        if not r or not c.execute('SELECT 1 FROM matriculas WHERE usuario_id=? AND curso_id=?', (u['id'], r['id'])).fetchone():
            return self.erro('Você não está matriculado neste curso.', 403)
        if d.get('desfazer'):
            c.execute('DELETE FROM progresso WHERE usuario_id=? AND curso_id=? AND aula_id=?', (u['id'], r['id'], d.get('aula')))
        else:
            c.execute('INSERT OR IGNORE INTO progresso VALUES (?,?,?,?)', (u['id'], r['id'], d.get('aula'), int(time.time())))
        total = contar_aulas(json.loads(r['modulos']))
        feitas = c.execute('SELECT COUNT(*) FROM progresso WHERE usuario_id=? AND curso_id=?', (u['id'], r['id'])).fetchone()[0]
        return self.json({'ok': True, 'feitas': feitas, 'total': total})

    # ------------------------------------------------ painel do aluno
    def r_aluno(self, c, d, m):
        u = self.exigir(c, 'aluno')
        if not u:
            return
        itens = []
        for mt in c.execute('SELECT * FROM matriculas WHERE usuario_id=? ORDER BY criado DESC', (u['id'],)).fetchall():
            r = c.execute('SELECT * FROM cursos WHERE id=?', (mt['curso_id'],)).fetchone()
            if not r:
                continue
            cp = curso_publico(r, c)
            mods = json.loads(r['modulos'])
            feitas = {x[0]: x[1] for x in c.execute('SELECT aula_id, criado FROM progresso WHERE usuario_id=? AND curso_id=?', (u['id'], r['id']))}
            proxima = next(({'id': a['id'], 'titulo': a['titulo']} for mm in mods for a in mm.get('aulas', []) if a['id'] not in feitas), None)
            cp.update({'feitas': len(feitas), 'proxima': proxima, 'matriculado_em': mt['criado'],
                       'ultima': max(feitas.values()) if feitas else mt['criado']})
            itens.append(cp)
        dias = sorted({time.strftime('%Y-%m-%d', time.localtime(x[0])) for x in
                       c.execute('SELECT criado FROM progresso WHERE usuario_id=?', (u['id'],))})
        return self.json({'cursos': itens, 'dias': dias})

    # ------------------------------------------------ professor e parceiro criador
    def r_estudio(self, c, d, m):
        u = self.exigir(c, 'professor', 'parceiro')
        if not u:
            return
        out = []
        for r in c.execute('SELECT * FROM cursos WHERE autor_id=? ORDER BY atualizado DESC', (u['id'],)).fetchall():
            cp = curso_publico(r, c)
            cp['motivo'] = r['motivo']
            cp['receita'] = c.execute('SELECT COALESCE(SUM(valor),0) FROM matriculas WHERE curso_id=?', (r['id'],)).fetchone()[0]
            cp['conclusoes'] = c.execute('SELECT COUNT(*) FROM progresso WHERE curso_id=?', (r['id'],)).fetchone()[0]
            out.append(cp)
        recentes = [dict(x) for x in c.execute('''SELECT u.nome, c.titulo, m.criado FROM matriculas m
                      JOIN usuarios u ON u.id=m.usuario_id JOIN cursos c ON c.id=m.curso_id
                      WHERE c.autor_id=? ORDER BY m.criado DESC LIMIT 8''', (u['id'],))]
        return self.json({'cursos': out, 'recentes': recentes})

    def r_estudio_curso(self, c, d, m):
        u = self.exigir(c, 'professor', 'parceiro')
        if not u:
            return
        if m == 'GET':
            r = c.execute('SELECT * FROM cursos WHERE id=? AND autor_id=?', (d.get('id'), u['id'])).fetchone()
            if not r:
                return self.erro('Curso não encontrado.', 404)
            x = dict(r)
            x['modulos'] = json.loads(r['modulos'])
            x['aprender'] = json.loads(r['aprender'] or '[]')
            x['requisitos'] = json.loads(r['requisitos'] or '[]')
            return self.json({'curso': x})
        titulo = (d.get('titulo') or '').strip()[:120]
        if len(titulo) < 4:
            return self.erro('Dê um título ao curso.')
        mods = []
        for mm in (d.get('modulos') or [])[:40]:
            aulas = []
            for a in (mm.get('aulas') or [])[:60]:
                t = (a.get('titulo') or '').strip()[:140]
                if not t:
                    continue
                aulas.append({'id': (a.get('id') or secrets.token_hex(4))[:16], 'titulo': t,
                              'min': max(0, min(600, int(a.get('min') or 0))), 'gratis': bool(a.get('gratis')),
                              'video': (a.get('video') or '').strip()[:300], 'texto': (a.get('texto') or '')[:20000]})
            if (mm.get('titulo') or '').strip() or aulas:
                mods.append({'titulo': (mm.get('titulo') or 'Módulo').strip()[:120], 'aulas': aulas})
        try:
            preco = max(0.0, min(9999.0, float(d.get('preco') or 0)))
        except ValueError:
            preco = 0.0
        campos = dict(titulo=titulo, resumo=(d.get('resumo') or '')[:240], descricao=(d.get('descricao') or '')[:6000],
                      categoria=(d.get('categoria') or 'Fundamentos')[:40], nivel=(d.get('nivel') or 'Iniciante')[:20],
                      preco=preco, cor=(d.get('cor') or 'lima')[:12], modulos=json.dumps(mods, ensure_ascii=False),
                      aprender=json.dumps(lista(d.get('aprender')), ensure_ascii=False),
                      requisitos=json.dumps(lista(d.get('requisitos')), ensure_ascii=False),
                      preco_original=max(0.0, min(9999.0, num(d.get('preco_original')))))
        acao = d.get('acao') or 'salvar'
        agora = int(time.time())
        if d.get('id'):
            r = c.execute('SELECT * FROM cursos WHERE id=? AND autor_id=?', (d['id'], u['id'])).fetchone()
            if not r:
                return self.erro('Curso não encontrado.', 404)
            status = r['status']
        else:
            status = 'rascunho'
        if acao == 'publicar':
            if not mods or not contar_aulas(mods):
                return self.erro('Adicione pelo menos uma aula antes de publicar.')
            # professor da casa publica direto; parceiro passa pela curadoria
            status = 'publicado' if u['papel'] == 'professor' else 'em_analise'
        elif acao == 'despublicar':
            status = 'rascunho'
        if d.get('id'):
            c.execute('''UPDATE cursos SET titulo=?,resumo=?,descricao=?,categoria=?,nivel=?,preco=?,cor=?,modulos=?,
                         aprender=?,requisitos=?,preco_original=?,status=?,atualizado=?, motivo=CASE WHEN ?='em_analise' THEN '' ELSE motivo END WHERE id=?''',
                      (*campos.values(), status, agora, status, d['id']))
            cid = d['id']
        else:
            slug = slugify(titulo)
            while c.execute('SELECT 1 FROM cursos WHERE slug=?', (slug,)).fetchone():
                slug = slugify(titulo)[:52] + '-' + secrets.token_hex(2)
            cur = c.execute('''INSERT INTO cursos (autor_id,slug,titulo,resumo,descricao,categoria,nivel,preco,cor,modulos,
                               aprender,requisitos,preco_original,status,criado,atualizado)
                               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                            (u['id'], slug, *campos.values(), status, agora, agora))
            cid = cur.lastrowid
        r = c.execute('SELECT slug, status FROM cursos WHERE id=?', (cid,)).fetchone()
        return self.json({'ok': True, 'id': cid, 'slug': r['slug'], 'status': r['status']})

    def r_estudio_excluir(self, c, d, m):
        u = self.exigir(c, 'professor', 'parceiro')
        if not u:
            return
        r = c.execute('SELECT id FROM cursos WHERE id=? AND autor_id=?', (d.get('id'), u['id'])).fetchone()
        if not r:
            return self.erro('Curso não encontrado.', 404)
        if c.execute('SELECT 1 FROM matriculas WHERE curso_id=?', (r['id'],)).fetchone():
            return self.erro('Este curso já tem alunos. Despublique em vez de excluir.')
        c.execute('DELETE FROM cursos WHERE id=?', (r['id'],))
        return self.json({'ok': True})

    # ------------------------------------------------ parceiro (afiliado)
    def r_parceiro(self, c, d, m):
        u = self.exigir(c, 'parceiro')
        if not u:
            return
        vendas = [dict(x) for x in c.execute('''SELECT c.titulo, m.valor, m.criado FROM matriculas m JOIN cursos c ON c.id=m.curso_id
                    WHERE m.ref_id=? ORDER BY m.criado DESC''', (u['id'],))]
        cliques = c.execute('SELECT COUNT(*) FROM cliques WHERE ref=?', (u['ref'],)).fetchone()[0]
        comissao = sum(v['valor'] for v in vendas) * COMISSAO_AFILIADO
        repasse = c.execute('''SELECT COALESCE(SUM(m.valor),0) FROM matriculas m JOIN cursos c ON c.id=m.curso_id
                               WHERE c.autor_id=?''', (u['id'],)).fetchone()[0] * REPASSE_CRIADOR
        serie = {}
        for v in vendas:
            k = time.strftime('%Y-%m-%d', time.localtime(v['criado']))
            serie[k] = serie.get(k, 0) + v['valor'] * COMISSAO_AFILIADO
        return self.json({'ref': u['ref'], 'cliques': cliques, 'vendas': vendas, 'comissao': comissao,
                          'repasse': repasse, 'taxa_afiliado': COMISSAO_AFILIADO, 'taxa_criador': REPASSE_CRIADOR,
                          'serie': serie})

    # ------------------------------------------------ curadoria (admin)
    def r_admin(self, c, d, m):
        u = self.exigir(c, 'admin')
        if not u:
            return
        fila = []
        for r in c.execute("SELECT * FROM cursos WHERE status='em_analise' ORDER BY atualizado").fetchall():
            cp = curso_publico(r, c, detalhado=True, liberado=True)
            fila.append(cp)
        contas = {p: c.execute('SELECT COUNT(*) FROM usuarios WHERE papel=?', (p,)).fetchone()[0] for p in PAPEIS}
        receita = c.execute('SELECT COALESCE(SUM(valor),0) FROM matriculas').fetchone()[0]
        return self.json({'fila': fila, 'contas': contas, 'receita': receita})

    def r_admin_decidir(self, c, d, m):
        u = self.exigir(c, 'admin')
        if not u:
            return
        status = 'publicado' if d.get('aprovar') else 'rascunho'
        c.execute("UPDATE cursos SET status=?, motivo=? WHERE id=? AND status='em_analise'",
                  (status, '' if d.get('aprovar') else (d.get('motivo') or 'Ajustes necessários.')[:400], d.get('id')))
        return self.json({'ok': True, 'status': status})


if __name__ == '__main__':
    sys.path.insert(0, ROOT)
    porta = int(sys.argv[1]) if len(sys.argv) > 1 else 5530
    criar_banco()
    print('Escola de IA rodando em http://localhost:%d' % porta)
    ThreadingHTTPServer(('127.0.0.1', porta), Handler).serve_forever()
