# Carrega .env.example e depois .env (para scripts bash). Uso: source scripts/config.sh
_raiz="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
_carregar() {
  [ -f "$1" ] || return 0
  while IFS='=' read -r k v; do
    [[ -z "$k" || "$k" == \#* ]] && continue
    v="${v%\"}"; v="${v#\"}"
    [[ " $_do_ambiente " == *" $k "* ]] && continue   # variável passada na linha de comando vence o .env
    export "$k=$v"
  done < "$1"
}
_do_ambiente="$(compgen -e | tr '\n' ' ')"
_carregar "$_raiz/.env.example"
_carregar "$_raiz/.env"
# Versão com barras invertidas para comandos do cmd.exe
export WIN_DIR_BS="${WIN_DIR//\//\\}"
export APPLIO_DIR_BS="${APPLIO_DIR//\//\\}"
