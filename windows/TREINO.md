# Treino de voz (RVC / Applio) — PC Windows

Guia para treinar um modelo de voz RVC no PC de treino (Windows + GPU NVIDIA, testado numa GTX 1660 de 6 GB).
Use só vozes de pessoas que consentiram.

## Onde fica cada coisa

| O quê | Caminho |
|---|---|
| Applio | `C:\Applio` |
| Áudios de treino (um diretório por voz) | `C:\MeuParca\dataset\<voz>\*.wav` |
| Script de treino | `C:\MeuParca\treinar.bat` |
| Log de cada treino | `C:\MeuParca\logs\<voz>_treino.log` |
| Modelo treinado | `C:\Applio\logs\<voz>\` |

## Já configurado (não precisa refazer)

- Precisão **fp32** (a série GTX 16 dá problema com fp16). Fica em `%APPDATA%\Applio\config.json`, `"precision": "fp32"`.
- Modelos pré-treinados baixados (HiFi-GAN 32k/40k/48k, rmvpe, contentvec).
- Servidor SSH (`sshd`) para o notebook mandar áudios e iniciar treinos.

## Fluxo normal

1. **Na estação de preparo**, coloque os áudios em `Audios/<voz>/` e rode `scripts/preparar.py <voz>`
   e depois `scripts/enviar.sh <voz>` (veja o README). Os WAVs chegam em `C:\MeuParca\dataset\<voz>\`.
2. **Treinar**: abra um terminal em `C:\MeuParca` e rode:
   ```
   treinar.bat joao
   ```
   Opcional: `treinar.bat joao 400 4` (épocas, batch size).
3. **Acompanhar**: abra `C:\MeuParca\logs\joao_treino.log`, ou rode `C:\Applio\run-tensorboard.bat`.
4. **Usar**: abra `C:\Applio\run-applio.bat` → aba **Inference** → escolha o modelo `joao`
   e o `.index` correspondente.

Ao treinar de novo uma voz que já tem modelo, o treino anterior **não é apagado**: o script move
`C:\Applio\logs\<voz>` para `C:\Applio\logs\<voz>_backup_<data>` e treina do zero com todos os
áudios da pasta. Isso é o certo quando você acrescenta áudios novos.

## Treino interrompido (reinício, queda de energia)

O Windows Update pode reiniciar o PC sozinho no meio do treino. Para retomar do último
checkpoint salvo (a cada 25 épocas), sem refazer as etapas anteriores:
```
continuar.bat joao
```
Use os mesmos valores de épocas e batch do treino original. **Não** use `treinar.bat` para isso,
porque ele recomeça do zero.

Para evitar o problema: antes de um treino longo, vá em **Configurações → Windows Update →
Pausar atualizações** (1 semana). Bloquear a tela não interrompe o treino; reiniciar, desligar
ou suspender, sim.

## O que o script faz (configurações)

| Etapa | Configuração | Por quê |
|---|---|---|
| Preprocess | 40 kHz, corte automático, normalização `post` | 40k é mais leve que 48k em 6 GB, com pouca perda |
| Extract | pitch `rmvpe`, embedder `contentvec`, GPU 0 | combinação padrão e mais robusta |
| Train | 300 épocas, batch 4, salva a cada 25, pré-treinado HiFi-GAN | faixa recomendada para 10–30 min de áudio |
| Index | `Auto` | melhora a fidelidade do timbre na inferência |

## Escolhendo épocas

- Menos de 10 min de áudio: 200–300 épocas.
- 10–30 min: 300–400 épocas.
- O script salva o modelo a cada 25 épocas (`joao_25e_...pth`, `joao_50e_...pth`, ...).
  Teste alguns: se a voz começa a ficar metálica ou robótica nas épocas mais altas, o modelo
  passou do ponto (overtraining), então use um checkpoint anterior.

## Problemas comuns

| Sintoma | Solução |
|---|---|
| `CUDA out of memory` | `treinar.bat joao 300 2` (batch menor) |
| Treino lento ou GPU parada | `nvidia-smi` deve mostrar `python.exe` usando a GPU |
| Resultado com chiado ou ruído | limpar os áudios antes (Demucs/UVR no notebook) e treinar de novo |
| Voz com sotaque, ritmo ou falhas | geralmente é pouco áudio; junte mais amostras |
| Notebook não conecta por SSH | `Get-Service sshd` deve estar `Running`; se sumiu, recrie com `New-Service -Name sshd -DisplayName "OpenSSH SSH Server" -BinaryPathName '"C:\Program Files\OpenSSH\sshd.exe"' -StartupType Automatic` e rode `Start-Service sshd` |
