# Meu Parça: seu parceiro virtual local, com a voz que você treinar

Esqueleto para criar, **no seu próprio computador**, um assistente de IA que conversa com você
usando uma voz treinada a partir de áudios (por exemplo, áudios de WhatsApp de um amigo que
topou a brincadeira), com uma personalidade baseada no jeito real dessa pessoa falar.

Tudo roda localmente: nenhum áudio, transcrição ou conversa sai das suas máquinas.

> **Regra do projeto:** use apenas vozes de pessoas que **consentiram**, para uso privado.
> Não use para se passar por alguém, enganar terceiros ou criar falas que a pessoa não aprovaria.

## Como funciona

```
Áudios/<voz>/       →  preparar.py   →  dataset/<voz>/          (WAV limpo, sem duplicatas)
                       transcrever.py → catalogo/<voz>.json     (o que a pessoa fala)
                       catalogar.py   → painel: tags, piadas, bordões, original × limpo
                       limpar.sh      → dataset/<voz>_limpo/    (Demucs: tira ruído/música)
                       enviar.sh      → PC com GPU: treinar.bat → modelo RVC da voz
personalidade/<voz>.md                → instruções para a IA falar como a pessoa
assistente/ (em construção)           → você fala → Whisper → LLM local → TTS → RVC → voz
```

Pensado para **duas máquinas** (funciona com uma só, se ela tiver GPU NVIDIA):

| Máquina | Papel |
|---|---|
| **Estação de preparo** (Linux/macOS; ex.: notebook) | guarda os áudios originais, converte, transcreve, cataloga, limpa |
| **PC de treino** (Windows + GPU NVIDIA) | treina o modelo de voz (Applio/RVC) e, no futuro, roda o assistente |

A estação de preparo controla o PC de treino por SSH.

## Requisitos

**Estação de preparo:** Python 3.10+, `ffmpeg`, `ssh`/`scp`, ~5 GB livres (modelos Whisper/Demucs).

**PC de treino:** Windows 10/11, GPU NVIDIA com 6 GB+ de VRAM, driver atualizado,
[Applio](https://github.com/IAHispano/Applio) e Servidor OpenSSH.

## Instalação

### 1. Estação de preparo

```bash
git clone https://github.com/lucaslpsilveira/Meu-Parca.git && cd Meu-Parca
python3 -m venv .venv
.venv/bin/pip install faster-whisper numpy
.venv/bin/pip install --index-url https://download.pytorch.org/whl/cpu torch torchaudio
.venv/bin/pip install demucs soundfile
cp .env.example .env          # e ajuste WIN_HOST, caminhos etc.
```

### 2. PC de treino (Windows)

1. **Applio**: baixe em `C:\Applio` e rode `run-install.bat`.
2. **Precisão fp32** (obrigatório na série GTX 16, recomendado em placas antigas): no Applio,
   *Settings → Precision → fp32*, ou edite `%APPDATA%\Applio\config.json` (`"precision": "fp32"`).
3. **Modelos pré-treinados**: `C:\Applio\env\python.exe C:\Applio\core.py prerequisites --pretraineds-hifigan --models --exe`
4. **Servidor SSH**: no PowerShell **como Administrador**, um comando por vez:
   ```powershell
   winget install --id Microsoft.OpenSSH.Preview
   Start-Service sshd
   Set-Service -Name sshd -StartupType Automatic
   New-NetFirewallRule -Name sshd-meuparca -DisplayName "OpenSSH Server" -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22 -Profile Any
   ```
   - Evite `Add-WindowsCapability ... OpenSSH.Server`: ele depende do Windows Update e costuma travar.
   - Se `Start-Service sshd` disser que o serviço não existe, crie-o:
     `New-Service -Name sshd -DisplayName "OpenSSH SSH Server" -BinaryPathName '"C:\Program Files\OpenSSH\sshd.exe"' -StartupType Automatic`
5. **Chave SSH** (para não precisar de senha). Na estação: `ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519_treino`.
   No Windows (Admin), se o seu usuário for administrador:
   ```powershell
   Add-Content C:\ProgramData\ssh\administrators_authorized_keys "<conteúdo do .pub>"
   icacls C:\ProgramData\ssh\administrators_authorized_keys /inheritance:r /grant "Administradores:F" /grant "SYSTEM:F"
   ```
   (Em Windows em inglês: `Administrators`.) Depois, na estação, adicione ao `~/.ssh/config`:
   ```
   Host meupc
       HostName 192.168.0.X
       User seu-usuario-windows
       IdentityFile ~/.ssh/id_ed25519_treino
       IdentitiesOnly yes
   ```
   e use `WIN_HOST=meupc` no `.env`. Teste com `ssh meupc whoami`.
6. Crie a pasta `C:\MeuParca` (ou o que estiver em `WIN_DIR`).

## Uso

### 1. Juntar os áudios

Coloque os áudios de uma pessoa em `Audios/<voz>/` (`.opus`, `.ogg`, `.mp3`, `.m4a`, `.wav`...).
Use um nome curto e sem espaços para a voz, ex.: `Audios/joao/`.

- Quanto mais, melhor: **10 a 30 min** de fala é o ideal para o RVC.
- Só a voz dessa pessoa: tire áudios em que outra pessoa fala.
- Variedade ajuda: rindo, falando baixo, empolgado, perguntando.

### 2. Preparar

```bash
.venv/bin/python scripts/preparar.py joao --simular   # mostra o que vai fazer
.venv/bin/python scripts/preparar.py joao
```

Converte para WAV mono 16-bit, numera (`joao_001.wav`...) e grava `dataset/joao_mapa.csv`
(qual WAV veio de qual original). **Duplicatas** (o mesmo áudio reencaminhado ou reencodado) e
áudios longos demais (junções de vários áudios) vão para `Audios/_descartados/joao/`.
É incremental: rode de novo quando chegarem áudios novos.

### 3. Transcrever e catalogar

```bash
.venv/bin/python scripts/transcrever.py joao
.venv/bin/python scripts/catalogar.py joao       # abre http://localhost:8765
```

No painel, para cada fala você pode:

- ouvir, e **corrigir o texto** (o Whisper erra gírias e nomes);
- marcar **Piada**, **Bordão**, **Complemento** (frase para o assistente usar de vez em quando),
  **Tocar original** (o assistente pode tocar o áudio real) ou **Ruim** (fica fora do treino);
- escrever **notas** de contexto ("usar quando algo der errado");
- **Excluir** um áudio que não é dessa pessoa;
- comparar **Original × Limpo** e escolher qual vai para o treino (depois do passo 4).

### 4. Limpar (opcional)

```bash
scripts/limpar.sh joao
```

Usa o Demucs para separar a voz de ruído e música, gerando `dataset/joao_limpo/`. Os originais
não são alterados. Compare no painel (filtro **Comparar limpo**) e escolha, em cada fala, qual
versão usar. Em áudios de WhatsApp já limpos a diferença costuma ser pequena.

### 5. Enviar e treinar

```bash
scripts/enviar.sh joao
```

Monta `dataset/joao_treino/` com as versões escolhidas (sem os "Ruim"), sincroniza com
`<WIN_DIR>\dataset\joao\` e atualiza os scripts de treino e o `config.env` no Windows.

No Windows (ou via SSH):

```
C:\MeuParca\treinar.bat joao            :: usa EPOCAS e BATCH do .env
C:\MeuParca\treinar.bat joao 400 4      :: épocas e batch personalizados
C:\MeuParca\continuar.bat joao          :: retoma um treino interrompido
```

O guia completo de treino (épocas, problemas comuns, uso no Applio) está em
[`windows/TREINO.md`](windows/TREINO.md).

> Para iniciar o treino remotamente sem ele morrer ao fechar o SSH, use uma tarefa agendada
> interativa: `schtasks /create /tn Treino /tr "cmd /k C:\MeuParca\treinar.bat joao" /sc once /st 23:59 /it /f`
> e depois `schtasks /run /tn Treino`.

### 6. Personalidade

Copie `personalidade/exemplo.md` para `personalidade/joao.md` e preencha com base no catálogo
(bordões, piadas, notas). Liste os áudios que podem ser tocados em `personalidade/joao_audios.json`
(modelo em `exemplo_audios.json`). Teste com o Ollama:

```bash
ollama run gemma3:4b   # cole o conteúdo de personalidade/joao.md como mensagem de sistema
```

### 7. Assistente (em construção)

Plano para uma GPU de 6 GB: **faster-whisper** (CPU) → **Ollama** com modelo de 3 a 4 bilhões de
parâmetros (GPU, ~3 GB) → **Piper** pt-BR (CPU) → **RVC** da voz (GPU, ~1,5 GB), tocando frase a frase
para responder rápido.

## Configuração (`.env`)

| Variável | Padrão | O que é |
|---|---|---|
| `WIN_HOST` | `meupc` | host SSH do PC de treino |
| `WIN_DIR` | `C:/MeuParca` | pasta do projeto no Windows |
| `APPLIO_DIR` | `C:/Applio` | instalação do Applio |
| `SAMPLE_RATE` | `40000` | taxa do modelo RVC (32000/40000/48000) |
| `EPOCAS`, `BATCH`, `SALVAR_A_CADA` | `300`, `4`, `25` | treino |
| `DATASET_SR` | `48000` | taxa dos WAVs em `dataset/` |
| `MAX_DURACAO` | `300` | áudios mais longos (s) são descartados no preparo |
| `WHISPER_MODELO`, `IDIOMA` | `large-v3-turbo`, `pt` | transcrição |
| `PORTA_CATALOGO` | `8765` | porta do painel |
| `LLM_MODELO` | `gemma3:4b` | modelo do Ollama para o assistente |

## Estrutura

```
scripts/         preparo, transcrição, painel, limpeza, envio (rodam na estação)
windows/         treinar.bat, continuar.bat, TREINO.md (copiados para o PC de treino)
personalidade/   exemplo.md e exemplo_audios.json (as suas ficam fora do Git)
Audios/ dataset/ catalogo/   seus dados (fora do Git)
```

## Privacidade

O `.gitignore` deixa de fora `Audios/`, `dataset/`, `catalogo/`, as personalidades reais, o `.env`
e o `CLAUDE.local.md`. Antes de publicar um fork, confira com `git status --ignored` que nenhum
áudio ou transcrição foi incluído.

## Problemas comuns

| Sintoma | Solução |
|---|---|
| Treino parou do nada | Windows Update reiniciou o PC: `continuar.bat <voz>`, e pause as atualizações antes de treinos longos |
| `Acesso negado` ao rodar o Python do Applio depois de reiniciar | `icacls C:\Applio\* /reset /T /C /Q` (Admin) |
| `CUDA out of memory` | batch menor: `treinar.bat <voz> 300 2` |
| SSH não conecta (timeout) | regra de firewall com `-Profile Any`; antivírus com firewall próprio |
| Voz robótica nas épocas finais | overtraining: use um checkpoint anterior (salvo a cada 25 épocas) |
