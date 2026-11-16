"""Dados de demonstração da Escola de IA. Rodado uma única vez, quando o banco é criado."""
import json, random, secrets, sqlite3, time

DIA = 86400


def aula(titulo, minutos, texto, gratis=False, video=''):
    return {'id': secrets.token_hex(4), 'titulo': titulo, 'min': minutos, 'gratis': gratis, 'video': video, 'texto': texto.strip()}


FUND = [
    {'titulo': 'O que é IA, de verdade', 'aulas': [
        aula('IA, aprendizado de máquina e modelos de linguagem', 9, '''
## Três nomes, uma família

**Inteligência artificial** é o guarda-chuva: qualquer sistema que executa tarefas que antes exigiam raciocínio humano.
Dentro dele está o **aprendizado de máquina**, em que o sistema aprende padrões a partir de exemplos em vez de seguir regras escritas à mão.
E dentro do aprendizado de máquina estão os **modelos de linguagem** (LLMs), treinados com enormes volumes de texto para prever a próxima palavra.

> Prever a próxima palavra parece pouco. Feito bilhões de vezes, com contexto, vira escrever, resumir, traduzir e programar.

## O que levar desta aula

- Um LLM não "consulta" a internet por padrão: ele responde com o que aprendeu no treino.
- Ele pode errar com confiança. Por isso conferir fatos importantes faz parte do trabalho.
- Quanto melhor o contexto que você dá, melhor a resposta que você recebe.
''', gratis=True),
        aula('Como um modelo "pensa": tokens e contexto', 11, '''
## Tokens

O modelo não lê letras nem palavras inteiras: lê **tokens**, pedaços de texto com cerca de 3 a 4 caracteres em média.
"Inteligência" pode virar `Intel` + `ig` + `ência`.

## Janela de contexto

É o quanto de texto o modelo consegue considerar de uma vez: sua pergunta, as instruções, os arquivos e a conversa até ali.
Quando a conversa passa do limite, o início começa a ser esquecido.

## Na prática

1. Coloque as informações mais importantes no começo ou no fim do pedido.
2. Em conversas longas, peça um resumo e comece uma nova com ele.
3. Cole o material de referência em vez de pedir para o modelo "lembrar".
''', gratis=True),
    ]},
    {'titulo': 'Usando no dia a dia', 'aulas': [
        aula('Seu primeiro pedido bem feito', 8, '''
## A fórmula PCR

- **Papel**: quem o modelo deve ser. "Você é um revisor de textos jurídicos."
- **Contexto**: o que ele precisa saber. Público, objetivo, restrições.
- **Resultado**: o formato da entrega. "Uma tabela com três colunas", "até 120 palavras".

```
Papel: você é um professor de matemática do ensino médio.
Contexto: meus alunos têm 15 anos e odeiam frações.
Resultado: 3 exemplos do cotidiano, cada um com uma pergunta de fixação.
```

Teste agora: escolha uma tarefa do seu trabalho e escreva o pedido com P, C e R.
''', gratis=True),
        aula('Quando não usar IA', 6, '''
## Situações em que vale parar

- Decisões médicas, jurídicas ou financeiras sem revisão de um profissional.
- Dados pessoais de clientes colados em ferramentas sem contrato de privacidade.
- Fatos recentes, quando a ferramenta não tem acesso à internet.

> Regra simples: se um erro causaria dano real, a IA rascunha e uma pessoa decide.
''', gratis=True),
    ]},
]

PROMPT = [
    {'titulo': 'Fundamentos do prompt', 'aulas': [
        aula('Anatomia de um prompt profissional', 12, '''
## As seis partes

1. **Objetivo** em uma frase.
2. **Contexto** do negócio e do público.
3. **Material de referência** delimitado, por exemplo entre tags `<documento>`.
4. **Regras** do que fazer e do que evitar.
5. **Exemplos** de entrada e saída.
6. **Formato** de resposta.

Prompts profissionais são mais parecidos com um briefing do que com uma pergunta.
''', gratis=True),
        aula('Exemplos que ensinam (few-shot)', 14, '''
## Mostre, não descreva

Dois ou três exemplos bem escolhidos valem mais que um parágrafo de instruções.
Varie os exemplos para o modelo entender o padrão, e não copiar um caso específico.
'''),
    ]},
    {'titulo': 'Técnicas avançadas', 'aulas': [
        aula('Pedir raciocínio passo a passo', 10, '''
## Pense antes de responder

Em problemas com várias etapas, peça para o modelo planejar antes de entregar a resposta final.
Separe o raciocínio da resposta com marcadores para poder usar só o resultado.
'''),
        aula('Encadeando prompts', 13, '''
## Uma tarefa, várias etapas

Quebre trabalhos grandes: extrair → analisar → redigir → revisar.
Cada etapa recebe a saída da anterior. Fica mais fácil achar onde algo deu errado.
'''),
        aula('Avaliando a qualidade das respostas', 11, '''
## Crie um gabarito

Antes de mudar o prompt, defina 10 entradas de teste e o que seria uma boa resposta para cada uma.
Mude uma coisa por vez e compare.
'''),
    ]},
]

AUTO = [
    {'titulo': 'Pensando em fluxos', 'aulas': [
        aula('O que vale automatizar', 9, '''
## O teste dos três R

Uma tarefa é boa candidata quando é **R**epetitiva, tem **R**egras claras e **R**ende tempo ao ser feita por uma máquina.
Comece listando tudo que você faz mais de três vezes por semana.
''', gratis=True),
        aula('Gatilhos, ações e dados', 12, '''
## A estrutura de todo fluxo

- **Gatilho**: o que inicia. Um e-mail chegou, um formulário foi enviado.
- **Ações**: o que acontece. Classificar, resumir, responder, salvar.
- **Dados**: o que passa de uma etapa para outra.
'''),
    ]},
    {'titulo': 'Mão na massa', 'aulas': [
        aula('Triagem de e-mails com IA', 18, '''
## Projeto do módulo

Montamos um fluxo que lê e-mails novos, classifica por assunto e urgência, e cria um rascunho de resposta para revisão.
'''),
        aula('Atendimento no WhatsApp com base de conhecimento', 22, '''
## Respostas com base nos seus documentos

Conectamos um assistente às perguntas frequentes da empresa e definimos quando ele deve passar a conversa para uma pessoa.
'''),
    ]},
]

IMG = [
    {'titulo': 'Direção de arte com IA', 'aulas': [
        aula('Vocabulário visual para prompts de imagem', 10, '''
## Fale como diretor de fotografia

Descreva **assunto**, **enquadramento**, **luz**, **lente**, **paleta** e **textura**.
"Retrato em plano médio, luz de janela lateral, lente 85mm, paleta terrosa, grão de filme."
''', gratis=True),
        aula('Consistência de marca', 14, '''
## Um guia que a IA consegue seguir

Transforme o manual da marca em um bloco de texto reutilizável: cores em hexadecimal, estilo de luz, o que nunca aparece.
'''),
    ]},
    {'titulo': 'Produção', 'aulas': [
        aula('Do rascunho à arte final', 16, '''
## Fluxo de trabalho

Gerar variações → escolher → refinar partes → ajustar no editor → exportar nos formatos de cada rede.
'''),
    ]},
]

CODE = [
    {'titulo': 'Programando em dupla com a IA', 'aulas': [
        aula('Como pedir código que funciona', 12, '''
## Dê o contexto do projeto

Informe linguagem, versão, bibliotecas já usadas e o trecho de código ao redor.
Peça também os testes: assim você valida antes de colar no projeto.

```python
# Peça: "escreva a função e 3 testes com pytest"
def soma_pares(nums):
    return sum(n for n in nums if n % 2 == 0)
```
''', gratis=True),
        aula('Lendo e revisando o que a IA escreveu', 10, '''
## Você continua responsável

Leia cada linha. Pergunte "por que isso?" quando algo parecer mágico.
Rode, teste e só então aceite.
'''),
    ]},
    {'titulo': 'Agentes de código', 'aulas': [
        aula('Agentes no terminal: o fluxo completo', 20, '''
## Planejar, editar, testar

Agentes de código leem o projeto, propõem um plano, editam arquivos e rodam os testes.
Seu papel muda: você define o objetivo, revisa o plano e aprova as mudanças.
'''),
        aula('Projeto: um site do zero em uma tarde', 35, '''
## Projeto final

Do briefing ao site publicado, com o agente fazendo o trabalho pesado e você tomando as decisões.
'''),
    ]},
]

NEG = [
    {'titulo': 'IA para quem empreende', 'aulas': [
        aula('Mapeando onde a IA economiza horas', 9, '''
## O raio-x da semana

Liste as tarefas da semana e marque quanto tempo cada uma leva. As que envolvem texto, planilhas e atendimento costumam ser as primeiras a ganhar com IA.
''', gratis=True),
        aula('Conteúdo para redes em uma hora por semana', 15, '''
## Calendário com IA

Defina pilares de conteúdo, gere um mês de pautas, escreva legendas no seu tom e agende.
'''),
        aula('Atendimento e propostas mais rápidos', 12, '''
## Modelos que se adaptam

Crie modelos de proposta e de resposta e use a IA para personalizá-los para cada cliente.
'''),
    ]},
]

AGENTES = [
    {'titulo': 'Entendendo agentes', 'aulas': [
        aula('Do chatbot ao agente', 11, '''
## A diferença

Um chatbot responde. Um **agente** decide quais passos dar, usa ferramentas (buscar, calcular, enviar) e verifica o resultado até cumprir o objetivo.
''', gratis=True),
        aula('Ferramentas e permissões', 13, '''
## Dê poder com limites

Cada ferramenta precisa de uma descrição clara, entradas bem definidas e um limite do que pode fazer sem pedir aprovação.
'''),
    ]},
    {'titulo': 'Construindo', 'aulas': [
        aula('Seu primeiro agente com a API', 25, '''
## O laço do agente

1. Enviar a tarefa e as ferramentas ao modelo.
2. Executar a ferramenta que ele pedir.
3. Devolver o resultado.
4. Repetir até ele responder sem pedir ferramenta.
'''),
        aula('Medindo e melhorando', 16, '''
## Avaliação contínua

Registre cada execução, crie casos de teste e acompanhe taxa de sucesso, custo e tempo.
'''),
    ]},
]

VIDEO = [
    {'titulo': 'Roteiro e produção', 'aulas': [
        aula('Roteiros curtos que prendem', 10, '''
## Gancho em 2 segundos

Abra com a promessa, entregue o conteúdo em blocos curtos e feche com uma ação clara.
''', gratis=True),
        aula('Gerando cenas e narração', 18, '''
## Montagem

Gere as cenas, a narração e as legendas, e monte tudo no editor no ritmo do roteiro.
'''),
    ]},
]

CURSOS = [
    ('prof1', 'Fundamentos de IA sem complicação', 'Entenda o que a IA faz, onde ela erra e como usar no seu dia a dia, sem jargão.',
     'Fundamentos', 'Iniciante', 0, 'lima', FUND,
     'O ponto de partida da Escola de IA. Em menos de uma hora você entende como os modelos de linguagem funcionam, aprende a escrever pedidos melhores e sabe quando é melhor não usar IA.'),
    ('prof1', 'Engenharia de Prompt na prática', 'As técnicas que separam respostas genéricas de entregas profissionais.',
     'Prompts', 'Intermediário', 197, 'coral', PROMPT,
     'Briefings completos, exemplos que ensinam, raciocínio passo a passo, encadeamento e avaliação. Cada aula termina com um exercício aplicado ao seu trabalho.'),
    ('prof2', 'Automações com IA', 'Fluxos que leem, classificam e respondem por você, com revisão humana onde importa.',
     'Automação', 'Intermediário', 297, 'ceu', AUTO,
     'Você aprende a identificar o que vale automatizar e monta dois fluxos completos: triagem de e-mails e atendimento com base de conhecimento.'),
    ('parc1', 'Imagens com IA para marcas', 'Direção de arte, consistência visual e fluxo de produção para redes sociais.',
     'Criação', 'Iniciante', 147, 'rosa', IMG,
     'Curso de parceiro criador. Aprenda a descrever imagens como um diretor de fotografia e mantenha a identidade da marca em todas as peças.'),
    ('prof2', 'Programando com assistentes de IA', 'Escreva, revise e teste código com IA, do primeiro script ao projeto completo.',
     'Programação', 'Intermediário', 347, 'violeta', CODE,
     'Para quem já programa ou quer começar. Como pedir código que funciona, revisar com critério e trabalhar com agentes de código no terminal.'),
    ('parc1', 'IA para pequenos negócios', 'Conteúdo, atendimento e propostas em menos tempo, sem equipe de tecnologia.',
     'Negócios', 'Iniciante', 97, 'ambar', NEG,
     'Curso de parceiro criador. Um mapa prático para empreendedores aplicarem IA nas tarefas que mais tomam tempo.'),
    ('prof1', 'Agentes de IA: do zero ao primeiro agente', 'Entenda, projete e construa um agente que usa ferramentas de verdade.',
     'Programação', 'Avançado', 397, 'lima', AGENTES,
     'Do conceito à implementação: o laço do agente, ferramentas com permissões, avaliação e melhoria contínua.'),
]


def popular(caminho, hash_senha):
    c = sqlite3.connect(caminho)
    agora = int(time.time())
    ids = {}

    def user(chave, nome, email, papel, senha, bio='', ref=None, tipo=''):
        sal, h = hash_senha(senha)
        cur = c.execute('INSERT INTO usuarios (nome,email,papel,sal,hash,bio,ref,parceiro_tipo,criado) VALUES (?,?,?,?,?,?,?,?,?)',
                        (nome, email, papel, sal, h, bio, ref, tipo, agora - 60 * DIA))
        ids[chave] = cur.lastrowid

    user('admin', 'Coordenação', 'admin@escoladeia.test', 'admin', 'admin123')
    user('prof1', 'Helena Duarte', 'professor@escoladeia.test', 'professor', 'prof123',
         'Engenheira de machine learning há 12 anos. Ensina IA para quem não é da área.')
    user('prof2', 'Rafael Moreira', 'rafael@escoladeia.test', 'professor', 'prof123',
         'Desenvolvedor e consultor de automação para pequenas e médias empresas.')
    user('parc1', 'Bianca Lopes', 'parceiro@escoladeia.test', 'parceiro', 'parceiro123',
         'Designer e criadora de conteúdo. Usa IA na produção visual de marcas desde 2022.', ref='bianca7f2', tipo='ambos')
    user('parc2', 'Diego Nunes', 'diego@escoladeia.test', 'parceiro', 'parceiro123',
         'Criador do canal Diego Explica IA.', ref='diego31a', tipo='afiliado')
    user('aluno', 'Marina Costa', 'aluno@escoladeia.test', 'aluno', 'aluno123')

    cursos = {}
    for i, (autor, titulo, resumo, cat, nivel, preco, cor, mods, desc) in enumerate(CURSOS):
        import re, unicodedata
        slug = re.sub(r'[^a-z0-9]+', '-', unicodedata.normalize('NFKD', titulo).encode('ascii', 'ignore').decode().lower()).strip('-')[:60]
        cur = c.execute('''INSERT INTO cursos (autor_id,slug,titulo,resumo,descricao,categoria,nivel,preco,cor,status,modulos,criado,atualizado)
                           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                        (ids[autor], slug, titulo, resumo, desc, cat, nivel, preco, cor, 'publicado',
                         json.dumps(mods, ensure_ascii=False), agora - (40 - i) * DIA, agora - (40 - i) * DIA))
        cursos[titulo] = (cur.lastrowid, preco, mods, ids[autor])

    # curso de parceiro aguardando curadoria
    c.execute('''INSERT INTO cursos (autor_id,slug,titulo,resumo,descricao,categoria,nivel,preco,cor,status,modulos,criado,atualizado)
                 VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)''',
              (ids['parc1'], 'video-com-ia-para-redes-sociais', 'Vídeo com IA para redes sociais',
               'Roteiro, cenas e narração para vídeos curtos.', 'Do gancho à edição final.', 'Criação', 'Iniciante', 127, 'coral',
               'em_analise', json.dumps(VIDEO, ensure_ascii=False), agora - 2 * DIA, agora - 2 * DIA))

    # alunos de exemplo, matrículas e progresso para os painéis terem vida
    rnd = random.Random(42)
    nomes = ['Ana Souza', 'Bruno Lima', 'Carla Mendes', 'Daniel Rocha', 'Elisa Prado', 'Fábio Teixeira', 'Gabriela Reis',
             'Henrique Alves', 'Isabela Martins', 'João Pedro Silva', 'Karen Oliveira', 'Lucas Fernandes', 'Mariana Ribeiro',
             'Natália Gomes', 'Otávio Barros', 'Paula Castro', 'Renato Dias', 'Sofia Almeida']
    alunos = []
    for n in nomes:
        sal, h = hash_senha(secrets.token_hex(8))
        email = n.lower().replace(' ', '.').encode('ascii', 'ignore').decode() + '@exemplo.test'
        cur = c.execute('INSERT INTO usuarios (nome,email,papel,sal,hash,criado) VALUES (?,?,?,?,?,?)',
                        (n, email, 'aluno', sal, h, agora - rnd.randint(5, 50) * DIA))
        alunos.append(cur.lastrowid)

    lista = list(cursos.values())
    for uid in alunos:
        for cid, preco, mods, autor in rnd.sample(lista, rnd.randint(1, 3)):
            quando = agora - rnd.randint(1, 30) * DIA
            ref = rnd.choice([None, None, ids['parc1'], ids['parc2']])
            if ref == autor:
                ref = None
            c.execute('INSERT INTO matriculas (usuario_id,curso_id,ref_id,valor,criado) VALUES (?,?,?,?,?)', (uid, cid, ref, preco, quando))
            aulas = [a['id'] for m in mods for a in m['aulas']]
            for a in aulas[:rnd.randint(0, len(aulas))]:
                c.execute('INSERT INTO progresso VALUES (?,?,?,?)', (uid, cid, a, quando + rnd.randint(0, 5) * DIA))

    # a aluna de demonstração já começou dois cursos
    for titulo, feitas in (('Fundamentos de IA sem complicação', 3), ('Engenharia de Prompt na prática', 1)):
        cid, preco, mods, _ = cursos[titulo]
        c.execute('INSERT INTO matriculas (usuario_id,curso_id,ref_id,valor,criado) VALUES (?,?,?,?,?)',
                  (ids['aluno'], cid, ids['parc2'], preco, agora - 6 * DIA))
        aulas = [a['id'] for m in mods for a in m['aulas']]
        for k, a in enumerate(aulas[:feitas]):
            c.execute('INSERT INTO progresso VALUES (?,?,?,?)', (ids['aluno'], cid, a, agora - (5 - k * 2) * DIA))

    for _ in range(140):
        c.execute('INSERT INTO cliques VALUES (?,?,?)', (rnd.choice(['bianca7f2', 'diego31a']), None, agora - rnd.randint(0, 30) * DIA))
    c.commit()
    c.close()
