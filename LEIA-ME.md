# Escola de IA

Portal de cursos de inteligência artificial com três áreas e logins separados:
**aluno**, **professor** e **parceiro** (afiliado e/ou criador de cursos), além da **coordenação**, que faz a curadoria.

## Abrir no computador

```bash
python server.py
```

Abra http://localhost:5530. Só precisa do Python 3.9 ou mais novo, sem instalar nada.
Na primeira vez o banco `dados/escola.db` é criado com cursos e contas de demonstração.
Para zerar tudo, apague a pasta `dados/` e rode de novo.

## Contas de demonstração

| Área | E-mail | Senha |
|---|---|---|
| Aluno | aluno@escoladeia.test | aluno123 |
| Professor | professor@escoladeia.test | prof123 |
| Parceiro | parceiro@escoladeia.test | parceiro123 |
| Coordenação | admin@escoladeia.test | admin123 (entrar por `entrar.html?perfil=admin`) |

Na tela de login há um botão que preenche a conta de teste da aba escolhida.
Troque ou remova essas contas antes de publicar.

## Páginas

| Página | O que é |
|---|---|
| `index.html` | Página inicial: rede neural interativa, catálogo, três áreas, simulador de ganhos do parceiro, dúvidas |
| `cursos.html` | Catálogo com busca e filtros por categoria e nível |
| `curso.html?c=slug` | Página do curso: módulos, aulas abertas, matrícula |
| `aula.html` | Player: vídeo (YouTube, Vimeo ou .mp4), texto da aula, anotações, marcar como concluída |
| `entrar.html` | Login e cadastro, com abas Aluno / Professor / Parceiro |
| `aluno.html` | Painel do aluno: continuar de onde parou, progresso, sequência de dias |
| `professor.html` | Painel do professor: cursos, alunos, receita, matrículas recentes |
| `parceiro.html` | Painel do parceiro: link de afiliado, cliques, vendas, comissão, cursos enviados |
| `editor.html` | Estúdio para criar e editar cursos (professor publica direto; parceiro envia para análise) |
| `admin.html` | Coordenação: aprovar ou devolver cursos de parceiros |

## Regras de negócio (em `server.py`)

- `COMISSAO_AFILIADO = 0.30`: o afiliado ganha 30% das matrículas feitas pelo link dele (o link vale 30 dias).
- `REPASSE_CRIADOR = 0.70`: o parceiro criador recebe 70% das vendas dos cursos dele.
- O mesmo e-mail pode ter contas diferentes em cada área.

## Ainda falta para ir ao ar

- **Pagamento**: hoje a matrícula de curso pago é liberada sem cobrança (modo demonstração). Próximo passo: Mercado Pago, Stripe ou Hotmart.
- **E-mails**: recuperação de senha e confirmação de cadastro.
- **Hospedagem**: o `server.py` precisa de um servidor com Python (ex.: Render, Railway, VPS).
