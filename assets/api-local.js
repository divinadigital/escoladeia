/* Escola de IA — modo demonstração sem servidor (GitHub Pages).
   Reproduz as rotas do server.py dentro do navegador. Os dados ficam no localStorage
   de cada visitante, partindo de assets/demo-db.js. */
(() => {
  'use strict';
  const CHAVE = 'eia-demo-db-v1', SESSAO = 'eia-demo-sessao';
  const COMISSAO_AFILIADO = 0.30, REPASSE_CRIADOR = 0.70;
  const agora = () => Math.floor(Date.now() / 1000);

  // ---------- banco ----------
  let db;
  function carregar() {
    try { db = JSON.parse(localStorage.getItem(CHAVE)); } catch (e) { db = null; }
    if (!db || !db.usuarios) {
      db = JSON.parse(JSON.stringify(window.EIA_DEMO_DB));
      // os dados foram gerados numa data fixa: traz tudo para "agora"
      const d = agora() - db.gerado;
      db.usuarios.forEach(x => x.criado += d);
      db.cursos.forEach(x => { x.criado += d; x.atualizado += d; });
      ['matriculas', 'progresso', 'cliques'].forEach(t => db[t].forEach(x => x.criado += d));
      salvar();
    }
  }
  function salvar() { try { localStorage.setItem(CHAVE, JSON.stringify(db)); } catch (e) {} }
  const prox = t => db[t].reduce((m, x) => Math.max(m, x.id || 0), 0) + 1;

  // ---------- utilidades ----------
  const erro = (msg, status = 400) => { throw Object.assign(new Error(msg), { status }); };
  const hex = b => [...new Uint8Array(b)].map(x => x.toString(16).padStart(2, '0')).join('');
  const deHex = h => new Uint8Array(h.match(/../g).map(x => parseInt(x, 16)));
  const aleatorio = n => hex(crypto.getRandomValues(new Uint8Array(n)));
  async function hashSenha(senha, sal) {
    sal = sal || aleatorio(16);
    const k = await crypto.subtle.importKey('raw', new TextEncoder().encode(senha), 'PBKDF2', false, ['deriveBits']);
    const bits = await crypto.subtle.deriveBits({ name: 'PBKDF2', salt: deHex(sal), iterations: 120000, hash: 'SHA-256' }, k, 256);
    return [sal, hex(bits)];
  }
  const slugify = t => (t.normalize('NFKD').replace(/[^\x00-\x7f]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 60)) || 'curso';
  const contarAulas = mods => mods.reduce((s, m) => s + (m.aulas || []).length, 0);
  const duracao = mods => mods.reduce((s, m) => s + (m.aulas || []).reduce((x, a) => x + (+a.min || 0), 0), 0);
  const dia = ts => { const d = new Date(ts * 1000); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`; };
  const usuarioPorId = id => db.usuarios.find(u => u.id === id);
  const matriculado = (uid, cid) => db.matriculas.some(m => m.usuario_id === uid && m.curso_id === cid);
  const perfil = u => ({ id: u.id, nome: u.nome, email: u.email, papel: u.papel, ref: u.ref, parceiro_tipo: u.parceiro_tipo, bio: u.bio });

  function eu() { let id; try { id = +localStorage.getItem(SESSAO); } catch (e) {} return id ? usuarioPorId(id) || null : null; }
  function exigir(...papeis) {
    const u = eu();
    if (!u) erro('Faça login para continuar.', 401);
    if (papeis.length && !papeis.includes(u.papel)) erro('Esta área é de outro tipo de conta.', 403);
    return u;
  }
  function iniciarSessao(u) { try { localStorage.setItem(SESSAO, u.id); } catch (e) {} return { usuario: perfil(u) }; }

  function cursoPublico(r, detalhado, liberado) {
    const mods = r.modulos || [], autor = usuarioPorId(r.autor_id);
    const d = {
      id: r.id, slug: r.slug, titulo: r.titulo, resumo: r.resumo, categoria: r.categoria, nivel: r.nivel, preco: r.preco, cor: r.cor,
      status: r.status, aulas: contarAulas(mods), minutos: duracao(mods), alunos: db.matriculas.filter(m => m.curso_id === r.id).length,
      autor: { id: autor.id, nome: autor.nome, bio: autor.bio, selo: autor.papel === 'professor' ? 'Professor da casa' : 'Parceiro criador' },
    };
    if (detalhado) {
      d.descricao = r.descricao;
      d.modulos = mods.map(m => ({ titulo: m.titulo || '', aulas: (m.aulas || []).map(a => ({ id: a.id, titulo: a.titulo || '', min: a.min || 0, gratis: !!a.gratis, tipo: a.video ? 'video' : 'texto', bloqueada: !(liberado || a.gratis) })) }));
    }
    return d;
  }

  // ---------- rotas ----------
  const R = {
    async cadastro(d) {
      const nome = (d.nome || '').trim(), email = (d.email || '').trim().toLowerCase(), senha = d.senha || '', papel = d.papel;
      if (!['aluno', 'professor', 'parceiro'].includes(papel)) erro('Tipo de conta inválido.');
      if (nome.length < 2) erro('Informe seu nome.');
      if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) erro('E-mail inválido.');
      if (senha.length < 6) erro('A senha precisa ter pelo menos 6 caracteres.');
      if (db.usuarios.some(u => u.email === email && u.papel === papel)) erro(`Já existe uma conta de ${papel} com este e-mail.`);
      const [sal, hash] = await hashSenha(senha);
      let ref = null, tipo = '';
      if (papel === 'parceiro') { tipo = ['afiliado', 'criador', 'ambos'].includes(d.parceiro_tipo) ? d.parceiro_tipo : 'ambos'; ref = slugify(nome.split(' ')[0]).slice(0, 10) + aleatorio(2); }
      const u = { id: prox('usuarios'), nome, email, papel, sal, hash, bio: '', ref, parceiro_tipo: tipo, criado: agora() };
      db.usuarios.push(u); salvar();
      return iniciarSessao(u);
    },
    async login(d) {
      const email = (d.email || '').trim().toLowerCase(), papel = d.papel;
      const u = db.usuarios.find(x => x.email === email && x.papel === papel);
      if (!u || (await hashSenha(d.senha || '', u.sal))[1] !== u.hash) {
        const outro = db.usuarios.find(x => x.email === email && x.papel !== papel);
        if (outro && !u) erro(`Este e-mail é de uma conta de ${outro.papel}. Troque a aba acima.`, 401);
        erro('E-mail ou senha incorretos.', 401);
      }
      return iniciarSessao(u);
    },
    eu() { const u = eu(); return { usuario: u ? perfil(u) : null }; },
    sair() { try { localStorage.removeItem(SESSAO); } catch (e) {} return { ok: true }; },
    perfil(d, m) {
      const u = exigir();
      if (m === 'POST') { u.nome = (d.nome || u.nome).trim().slice(0, 80); u.bio = (d.bio || '').trim().slice(0, 400); salvar(); }
      return { usuario: perfil(u) };
    },
    cursos() {
      const cursos = db.cursos.filter(c => c.status === 'publicado').sort((a, b) => a.id - b.id).map(c => cursoPublico(c));
      return { cursos, stats: { cursos: cursos.length, aulas: cursos.reduce((s, c) => s + c.aulas, 0), alunos: db.usuarios.filter(u => u.papel === 'aluno').length, criadores: new Set(cursos.map(c => c.autor.id)).size } };
    },
    curso(d) {
      const r = db.cursos.find(c => c.slug === d.slug || c.id === +d.id);
      if (!r) erro('Curso não encontrado.', 404);
      const u = eu(), dono = u && (u.id === r.autor_id || u.papel === 'admin');
      if (r.status !== 'publicado' && !dono) erro('Curso não encontrado.', 404);
      const mat = !!(u && matriculado(u.id, r.id));
      const feitas = u ? db.progresso.filter(p => p.usuario_id === u.id && p.curso_id === r.id).map(p => p.aula_id) : [];
      return { curso: cursoPublico(r, true, mat || dono), matriculado: mat, feitas };
    },
    clique(d) {
      const ref = (d.ref || '').slice(0, 20);
      if (ref && db.usuarios.some(u => u.ref === ref)) { db.cliques.push({ ref, curso_id: d.curso_id || null, criado: agora() }); salvar(); }
      return { ok: true };
    },
    matricular(d) {
      const u = exigir('aluno');
      const r = db.cursos.find(c => c.id === +d.curso_id && c.status === 'publicado');
      if (!r) erro('Curso indisponível.', 404);
      const ref = db.usuarios.find(x => x.ref === (d.ref || '').slice(0, 20) && x.papel === 'parceiro');
      if (!matriculado(u.id, r.id)) { db.matriculas.push({ id: prox('matriculas'), usuario_id: u.id, curso_id: r.id, ref_id: ref && ref.id !== r.autor_id ? ref.id : null, valor: r.preco, criado: agora() }); salvar(); }
      return { ok: true, slug: r.slug };
    },
    aula(d) {
      const u = eu(), r = db.cursos.find(c => c.slug === d.curso);
      if (!r) erro('Curso não encontrado.', 404);
      const aula = r.modulos.flatMap(m => m.aulas || []).find(a => a.id === d.aula);
      if (!aula) erro('Aula não encontrada.', 404);
      const lib = aula.gratis || (u && (u.id === r.autor_id || u.papel === 'admin' || matriculado(u.id, r.id)));
      if (!lib) erro('Matricule-se para assistir a esta aula.', 403);
      return { aula };
    },
    concluir(d) {
      const u = exigir('aluno'), r = db.cursos.find(c => c.slug === d.curso);
      if (!r || !matriculado(u.id, r.id)) erro('Você não está matriculado neste curso.', 403);
      const i = db.progresso.findIndex(p => p.usuario_id === u.id && p.curso_id === r.id && p.aula_id === d.aula);
      if (d.desfazer) { if (i >= 0) db.progresso.splice(i, 1); }
      else if (i < 0) db.progresso.push({ usuario_id: u.id, curso_id: r.id, aula_id: d.aula, criado: agora() });
      salvar();
      return { ok: true, feitas: db.progresso.filter(p => p.usuario_id === u.id && p.curso_id === r.id).length, total: contarAulas(r.modulos) };
    },
    aluno() {
      const u = exigir('aluno');
      const cursos = db.matriculas.filter(m => m.usuario_id === u.id).sort((a, b) => b.criado - a.criado).map(mt => {
        const r = db.cursos.find(c => c.id === mt.curso_id); if (!r) return null;
        const cp = cursoPublico(r), feitas = {};
        db.progresso.filter(p => p.usuario_id === u.id && p.curso_id === r.id).forEach(p => feitas[p.aula_id] = p.criado);
        const a = r.modulos.flatMap(m => m.aulas || []).find(x => !(x.id in feitas));
        const ts = Object.values(feitas);
        return Object.assign(cp, { feitas: ts.length, proxima: a ? { id: a.id, titulo: a.titulo } : null, matriculado_em: mt.criado, ultima: ts.length ? Math.max(...ts) : mt.criado });
      }).filter(Boolean);
      const dias = [...new Set(db.progresso.filter(p => p.usuario_id === u.id).map(p => dia(p.criado)))].sort();
      return { cursos, dias };
    },
    estudio() {
      const u = exigir('professor', 'parceiro');
      const cursos = db.cursos.filter(c => c.autor_id === u.id).sort((a, b) => b.atualizado - a.atualizado).map(r => Object.assign(cursoPublico(r), {
        motivo: r.motivo, receita: db.matriculas.filter(m => m.curso_id === r.id).reduce((s, m) => s + m.valor, 0),
        conclusoes: db.progresso.filter(p => p.curso_id === r.id).length,
      }));
      const meus = new Set(db.cursos.filter(c => c.autor_id === u.id).map(c => c.id));
      const recentes = db.matriculas.filter(m => meus.has(m.curso_id)).sort((a, b) => b.criado - a.criado).slice(0, 8)
        .map(m => ({ nome: usuarioPorId(m.usuario_id)?.nome || '—', titulo: db.cursos.find(c => c.id === m.curso_id).titulo, criado: m.criado }));
      return { cursos, recentes };
    },
    'estudio/curso'(d, m) {
      const u = exigir('professor', 'parceiro');
      if (m === 'GET') {
        const r = db.cursos.find(c => c.id === +d.id && c.autor_id === u.id);
        if (!r) erro('Curso não encontrado.', 404);
        return { curso: JSON.parse(JSON.stringify(r)) };
      }
      const titulo = (d.titulo || '').trim().slice(0, 120);
      if (titulo.length < 4) erro('Dê um título ao curso.');
      const mods = [];
      (d.modulos || []).slice(0, 40).forEach(mm => {
        const aulas = (mm.aulas || []).slice(0, 60).map(a => ({ id: (a.id || aleatorio(4)).slice(0, 16), titulo: (a.titulo || '').trim().slice(0, 140), min: Math.max(0, Math.min(600, +a.min || 0)), gratis: !!a.gratis, video: (a.video || '').trim().slice(0, 300), texto: (a.texto || '').slice(0, 20000) })).filter(a => a.titulo);
        if ((mm.titulo || '').trim() || aulas.length) mods.push({ titulo: (mm.titulo || 'Módulo').trim().slice(0, 120), aulas });
      });
      const campos = { titulo, resumo: (d.resumo || '').slice(0, 240), descricao: (d.descricao || '').slice(0, 6000), categoria: (d.categoria || 'Fundamentos').slice(0, 40), nivel: (d.nivel || 'Iniciante').slice(0, 20), preco: Math.max(0, Math.min(9999, +d.preco || 0)), cor: (d.cor || 'lima').slice(0, 12), modulos: mods };
      const acao = d.acao || 'salvar';
      let r = d.id ? db.cursos.find(c => c.id === +d.id && c.autor_id === u.id) : null;
      if (d.id && !r) erro('Curso não encontrado.', 404);
      let status = r ? r.status : 'rascunho';
      if (acao === 'publicar') { if (!contarAulas(mods)) erro('Adicione pelo menos uma aula antes de publicar.'); status = u.papel === 'professor' ? 'publicado' : 'em_analise'; }
      else if (acao === 'despublicar') status = 'rascunho';
      if (r) { Object.assign(r, campos, { status, atualizado: agora() }); if (status === 'em_analise') r.motivo = ''; }
      else {
        let slug = slugify(titulo); while (db.cursos.some(c => c.slug === slug)) slug = slugify(titulo).slice(0, 52) + '-' + aleatorio(2);
        r = Object.assign({ id: prox('cursos'), autor_id: u.id, slug, motivo: '', criado: agora(), atualizado: agora(), status }, campos);
        db.cursos.push(r);
      }
      salvar();
      return { ok: true, id: r.id, slug: r.slug, status: r.status };
    },
    'estudio/excluir'(d) {
      const u = exigir('professor', 'parceiro'), i = db.cursos.findIndex(c => c.id === +d.id && c.autor_id === u.id);
      if (i < 0) erro('Curso não encontrado.', 404);
      if (db.matriculas.some(m => m.curso_id === db.cursos[i].id)) erro('Este curso já tem alunos. Despublique em vez de excluir.');
      db.cursos.splice(i, 1); salvar();
      return { ok: true };
    },
    parceiro() {
      const u = exigir('parceiro');
      const vendas = db.matriculas.filter(m => m.ref_id === u.id).sort((a, b) => b.criado - a.criado).map(m => ({ titulo: db.cursos.find(c => c.id === m.curso_id)?.titulo || '—', valor: m.valor, criado: m.criado }));
      const meus = new Set(db.cursos.filter(c => c.autor_id === u.id).map(c => c.id));
      const serie = {};
      vendas.forEach(v => { const k = dia(v.criado); serie[k] = (serie[k] || 0) + v.valor * COMISSAO_AFILIADO; });
      return {
        ref: u.ref, cliques: db.cliques.filter(c => c.ref === u.ref).length, vendas, serie,
        comissao: vendas.reduce((s, v) => s + v.valor, 0) * COMISSAO_AFILIADO,
        repasse: db.matriculas.filter(m => meus.has(m.curso_id)).reduce((s, m) => s + m.valor, 0) * REPASSE_CRIADOR,
        taxa_afiliado: COMISSAO_AFILIADO, taxa_criador: REPASSE_CRIADOR,
      };
    },
    admin() {
      exigir('admin');
      const contas = {}; ['aluno', 'professor', 'parceiro', 'admin'].forEach(p => contas[p] = db.usuarios.filter(u => u.papel === p).length);
      return { fila: db.cursos.filter(c => c.status === 'em_analise').sort((a, b) => a.atualizado - b.atualizado).map(c => cursoPublico(c, true, true)), contas, receita: db.matriculas.reduce((s, m) => s + m.valor, 0) };
    },
    'admin/decidir'(d) {
      exigir('admin');
      const r = db.cursos.find(c => c.id === +d.id && c.status === 'em_analise');
      if (r) { r.status = d.aprovar ? 'publicado' : 'rascunho'; r.motivo = d.aprovar ? '' : (d.motivo || 'Ajustes necessários.').slice(0, 400); salvar(); }
      return { ok: true, status: d.aprovar ? 'publicado' : 'rascunho' };
    },
  };

  window.EIA_LOCAL = {
    async chamar(rota, dados, metodo) {
      if (!db) carregar();
      const fn = R[rota];
      if (!fn) erro('Rota não encontrada.', 404);
      return JSON.parse(JSON.stringify(await fn(dados || {}, metodo)));
    },
    zerar() { try { localStorage.removeItem(CHAVE); localStorage.removeItem(SESSAO); } catch (e) {} db = null; },
  };
})();
