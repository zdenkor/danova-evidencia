#!/bin/bash
# Skript na vytvorenie novej verzie
# Použitie: ./new-version.sh "Popis zmien"

if [ -z "$1" ]; then
    echo "Použitie: ./new-version.sh \"Popis zmien\""
    echo "Príklad: ./new-version.sh \"Oprava chyby v exporte\""
    exit 1
fi

POPIS="$1"
DATUM=$(date +%Y-%m-%d)

# Získaj posledné poradové číslo z git tagov
LAST_TAG=$(git tag --sort=-v:refname 2>/dev/null | head -n 1)

if [ -z "$LAST_TAG" ]; then
    # Ak nie sú žiadne tagy, začni od 0001
    NOVE_CISLO="0001"
else
    # Extrahuj posledné 4 číslice z tagu
    LAST_NUM=${LAST_TAG: -4}
    # Odstráň leading zeros
    LAST_NUM=$((10#$LAST_NUM))
    NOVE_CISLO=$((LAST_NUM + 1))
    # Formátuj s leading zeros
    printf -v NOVE_CISLO "%04d" $NOVE_CISLO
fi

VERZIA="${DATUM}-${NOVE_CISLO}"
TAG="v${VERZIA}"

echo "========================================"
echo "Vytváram novú verziu: ${VERZIA}"
echo "========================================"

# Pridaj záznam do VERSION.md
cat >> VERSION.md << EOF

---

## ${VERZIA}

### Zmeny
- ${POPIS}
EOF

git add VERSION.md
git commit -m "Release ${VERZIA}

${POPIS}"
git tag -a "${TAG}" -m "Version ${VERZIA}: ${POPIS}"
git push origin master --tags

echo ""
echo "✓ Verzia ${VERZIA} bola vytvorená a pushnutá!"
echo "  Tag: ${TAG}"
echo ""
