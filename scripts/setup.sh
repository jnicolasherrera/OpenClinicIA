#!/bin/bash
# ============================================================
# OpenClinicIA — Setup Script
# Ejecutar: bash scripts/setup.sh
# ============================================================
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}"
echo "  ___                    ____ _ _       _      ___    _    "
echo " / _ \ _ __   ___ _ __ / ___| (_)_ __ (_) __ |_ _|  / \   "
echo "| | | | '_ \ / _ \ '_ \ |   | | | '_ \| |/ _\` | |  / _ \  "
echo "| |_| | |_) |  __/ | | | |___| | | | | | | (_| | | / ___ \ "
echo " \___/| .__/ \___|_| |_|\____|_|_|_| |_|_|\__,_|___/_/   \_\\"
echo "      |_|                                                    "
echo -e "${NC}"
echo "🏥 OpenClinicIA — Setup inicial"
echo "================================"

# ── 1. Verificar dependencias ─────────────────────────────────
echo ""
echo -e "${YELLOW}[1/6] Verificando dependencias...${NC}"

check_cmd() {
  if ! command -v $1 &> /dev/null; then
    echo -e "${RED}❌ '$1' no encontrado. Instalalo antes de continuar.${NC}"
    exit 1
  else
    echo "  ✅ $1 $(${1} --version 2>&1 | head -1)"
  fi
}

check_cmd git
check_cmd docker
check_cmd python3
check_cmd node
check_cmd gh   # GitHub CLI — necesario para crear el repo

# ── 2. Configurar .env ────────────────────────────────────────
echo ""
echo -e "${YELLOW}[2/6] Configurando variables de entorno...${NC}"

if [ ! -f .env ]; then
  cp .env.example .env
  echo "  ✅ .env creado desde .env.example"
  echo -e "  ${YELLOW}⚠️  Editá .env con tus API keys antes de continuar${NC}"
  echo ""
  read -p "  ¿Querés editar .env ahora? (s/n): " EDIT_ENV
  if [ "$EDIT_ENV" = "s" ]; then
    ${EDITOR:-nano} .env
  fi
else
  echo "  ✅ .env ya existe — saltando"
fi

# ── 3. Crear repositorio en GitHub ───────────────────────────
echo ""
echo -e "${YELLOW}[3/6] Creando repositorio público en GitHub...${NC}"

if gh repo view jnicolasherrera/OpenClinicIA &>/dev/null; then
  echo "  ✅ Repositorio ya existe en GitHub — saltando creación"
else
  gh repo create jnicolasherrera/OpenClinicIA \
    --public \
    --description "🏥 Plataforma open-source para gestión clínica con IA integrada — Ambient Scribe, Triaje NLP, Historia Clínica EHR" \
    --homepage "https://github.com/jnicolasherrera/OpenClinicIA" \
    --add-readme=false
  echo "  ✅ Repositorio creado: https://github.com/jnicolasherrera/OpenClinicIA"
fi

# ── 4. Inicializar Git y primer push ─────────────────────────
echo ""
echo -e "${YELLOW}[4/6] Inicializando Git y subiendo código...${NC}"

if [ ! -d .git ]; then
  git init
  git branch -M main
  echo "  ✅ Git inicializado"
fi

if ! git remote get-url origin &>/dev/null; then
  git remote add origin https://github.com/jnicolasherrera/OpenClinicIA.git
  echo "  ✅ Remote 'origin' configurado"
fi

git add .
git commit -m "feat: initial commit — vault brain_OC + arquitectura base OpenClinicIA

- Vault Obsidian brain_OC con documentación completa
- 00_TABLERO_PRINCIPAL, 01_ARQUITECTURA_MAESTRA, 02_ESTANDARES_CODING
- 03_MODULOS (8 módulos documentados), 04_APRENDIZAJE_CONTINUO_IA
- 05_STACK_TECNOLOGICO, 06_ROADMAP (5 fases), 07_DECISIONES_ARQUITECTURA
- 08_COSTOS_OPEX, 09_PRIVACIDAD_LEGAL, 10_CONTRIBUIR, 11_ESTADO_DIARIO
- Templates Obsidian (módulo + ADR)
- CLAUDE.md con sistema multi-agente (5 roles especializados)
- docker-compose.yml con stack completo
- README.md, LICENSE (MIT), CONTRIBUTING.md, CODE_OF_CONDUCT.md
- .env.example, .gitignore" 2>/dev/null || echo "  ✅ Sin cambios nuevos para commitear"

git push -u origin main
echo "  ✅ Código subido a GitHub"

# ── 5. Configurar GitHub ──────────────────────────────────────
echo ""
echo -e "${YELLOW}[5/6] Configurando repo en GitHub...${NC}"

# Topics
gh repo edit jnicolasherrera/OpenClinicIA \
  --add-topic "open-source" \
  --add-topic "healthcare" \
  --add-topic "ai" \
  --add-topic "fastapi" \
  --add-topic "nextjs" \
  --add-topic "claude-api" \
  --add-topic "medical" \
  --add-topic "ehr" \
  --add-topic "latam" \
  --add-topic "python" 2>/dev/null || true

# Habilitar Issues y Discussions
gh repo edit jnicolasherrera/OpenClinicIA \
  --enable-issues \
  --enable-discussions 2>/dev/null || true

echo "  ✅ Topics y features configurados"

# Crear labels útiles para issues
echo "  📌 Creando labels..."
gh label create "módulo: agenda" --color "0075ca" --repo jnicolasherrera/OpenClinicIA 2>/dev/null || true
gh label create "módulo: EHR" --color "0075ca" --repo jnicolasherrera/OpenClinicIA 2>/dev/null || true
gh label create "módulo: ambient-scribe" --color "e4e669" --repo jnicolasherrera/OpenClinicIA 2>/dev/null || true
gh label create "módulo: triaje-ia" --color "e4e669" --repo jnicolasherrera/OpenClinicIA 2>/dev/null || true
gh label create "fase: 1-bunker" --color "d4c5f9" --repo jnicolasherrera/OpenClinicIA 2>/dev/null || true
gh label create "fase: 2-oido" --color "d4c5f9" --repo jnicolasherrera/OpenClinicIA 2>/dev/null || true
gh label create "buena-primera-issue" --color "7057ff" --repo jnicolasherrera/OpenClinicIA 2>/dev/null || true
gh label create "se-busca-médico" --color "e11d48" --repo jnicolasherrera/OpenClinicIA 2>/dev/null || true
echo "  ✅ Labels creados"

# ── 6. Levantar stack local ───────────────────────────────────
echo ""
echo -e "${YELLOW}[6/6] Levantando stack de desarrollo...${NC}"

read -p "  ¿Levantar Docker Compose ahora? (s/n): " START_DOCKER
if [ "$START_DOCKER" = "s" ]; then
  docker compose up -d
  echo ""
  echo "  ✅ Stack corriendo:"
  echo "     → Frontend:  http://localhost:3000"
  echo "     → API docs:  http://localhost:8000/docs"
  echo "     → n8n:       http://localhost:5678"
  echo "     → MinIO:     http://localhost:9001"
fi

# ── Resumen final ─────────────────────────────────────────────
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  ✅ OpenClinicIA setup completado                        ║${NC}"
echo -e "${GREEN}╠══════════════════════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║  📁 Vault:   brain_OC/ (abrir con Obsidian)              ║${NC}"
echo -e "${GREEN}║  🐙 GitHub:  github.com/jnicolasherrera/OpenClinicIA     ║${NC}"
echo -e "${GREEN}║  🤖 Claude:  claude --dangerously-skip-permissions       ║${NC}"
echo -e "${GREEN}║  📖 Docs:    brain_OC/00_TABLERO_PRINCIPAL.md            ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "  Próximo paso:"
echo "  1. Abrí brain_OC/ en Obsidian"
echo "  2. Leé brain_OC/00_TABLERO_PRINCIPAL.md"
echo "  3. Arrancá Claude Code: claude"
echo ""
