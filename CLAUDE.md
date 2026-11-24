# Meu Parça: assistente local com voz treinada (RVC) e personalidade

Manual de uso completo no `README.md`. Detalhes da máquina do usuário (host, IP, estado atual)
ficam em `CLAUDE.local.md`, que não vai para o Git.

## Arquitetura
- **Estação de preparo** (Linux): áudios originais e scripts em `scripts/`. Controla o PC de treino via SSH.
- **PC de treino** (Windows + GPU NVIDIA): Applio em `APPLIO_DIR`, projeto em `WIN_DIR` (dataset, .bat, logs).
  Shell remoto via SSH é **cmd.exe** (use `powershell -NoProfile -Command` quando precisar).
- Configuração única no `.env` (modelo em `.env.example`), lida por `scripts/config.py` e `scripts/config.sh`;
  `enviar.sh` gera `<WIN_DIR>\config.env` para os .bat.

## Fluxo
`Audios/<voz>/` → `preparar.py` (WAV mono 16-bit, dedupe por hash + correlação de forma de onda, mapa CSV)
→ `transcrever.py` (faster-whisper, CPU) → `catalogar.py` (painel em localhost: tags piada/bordao/complemento/
tocar_original/ruim, notas, excluir, escolha original×limpo) → `limpar.sh` (Demucs, opcional)
→ `enviar.sh` (monta `dataset/<voz>_treino` via `montar_treino.py`, sincroniza, atualiza scripts)
→ `treinar.bat <voz>` / `continuar.bat <voz>` no Windows.

## Regras e armadilhas
- GPUs GTX 16xx: treinar sempre em **fp32** (`%APPDATA%\Applio\config.json`).
- Treino remoto: rodar via tarefa agendada interativa (`schtasks ... /it` + `/run`), senão morre com a sessão SSH.
- **Nunca sobrescrever um .bat em execução** no Windows (o cmd lê o arquivo aos poucos); `enviar.sh` já checa isso.
- Treino interrompido (Windows Update reinicia o PC): `continuar.bat`, nunca `treinar.bat` (que recomeça do zero).
- Não usar áudios gerados pelo modelo para retreinar (model collapse); só gravações reais.
- Dados pessoais (`Audios/`, `dataset/`, `catalogo/`, `personalidade/<voz>*`, `.env`) nunca entram no Git.

## Regra do projeto
Usar só vozes de pessoas que consentiram, para uso privado. Nada de se passar por alguém.
