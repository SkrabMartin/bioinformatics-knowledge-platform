# Lokální staging a předání VPS Codex

Stav ověření: 2026-11-07. Používat z kořene BKP.

## Skutečný stav

Implementace má verzi 0.7.0: FastAPI, explicitní SQLAlchemy vztahy a provenance,
šest Alembic revizí (head `20261023_0006`), PostgreSQL search, PubMed,
graf a přímé pathway/GO anotace. Frontend je React/TypeScript/Vite.
ARCHITECTURE.md a vydané položky CHANGELOG.md končí převážně fází 4;
aktuální funkce popisuje README a zdrojový kód.

Chybí globální autentizace starších zápisových API. Admin token chrání jen
vybrané novější operace. Health endpoint ověřuje proces, nikoli databázi;
proto je nutné ověřit i skutečný databázový GET.
Neexistuje automatický vědecký import GO/pathways ani enrichment engine.
Lokální staging začíná prázdný; fixture loader se zde vůbec nespouští.

## Spuštění

`compose.preview.yml` je samostatný soubor, **nekombinovat** s vývojovým Compose.
Používá vlastní projekt `bkp-local-preview`, vlastní volume a sítě.
Databáze je na interní síti bez publikovaného portu; backend rovněž nemá host port.
Pouze nginx publikuje `127.0.0.1:8088`. API je přes něj dostupné jen GET/HEAD.
Frontend má statický produkční build s `VITE_API_BASE_URL=/api/v1`, SPA fallback;
HMR ani WebSocket není potřeba. Backend běží bez reloadu a bez bind mountů.
Migrační jednorázová služba musí úspěšně skončit před startem backendu.

```bash
python3 scripts/init-preview.py
docker compose --env-file .env.preview -f compose.preview.yml config --quiet
docker compose --env-file .env.preview -f compose.preview.yml up -d --build
docker compose --env-file .env.preview -f compose.preview.yml ps -a
curl --fail http://127.0.0.1:8088/api/health
curl --fail http://127.0.0.1:8088/api/v1/genes
```

Inicializátor vytváří ignorovaný soubor `.env.preview` s právy 0600 a náhodným
hexadecimálním heslem vhodným pro URL. Existující soubor nikdy nepřepisuje.
Heslo po vytvoření volume neměnit bez koordinované změny PostgreSQL role.
Nevypisovat plný `docker compose config` ani prostředí kontejnerů: obsahují secrets.
Secrets jsou lokální konfigurace; provozní Docker administrátor k nim má přístup.
Nejde o plně hardened veřejnou produkci: backend dependencies mají rozsahy verzí,
base images nejsou připnuté na digest a není zavedena automatická zálohovací politika.

Dev konfigurace zůstává oddělená: `docker compose up --build` spouští Vite,
reload a výslovně označené demo fixtures. Porty 8000/5173 jsou pouze localhost;
DB nemá publikovaný port. Native backend potřebuje vlastní lokální PostgreSQL.

## Aktualizace, záloha a rollback

Před migrací existujících cenných dat zastavit zápisy, vytvořit privátní zálohu
a ověřit obnovu v oddělené databázi. První zde připravený start migruje nové volume.
Příklad zálohy (výstup obsahuje data; necommitovat):

```bash
umask 077
docker compose --env-file .env.preview -f compose.preview.yml exec -T db \
  pg_dump -U bkp -d bkp -Fc > /bezpecna/cesta/bkp-before-update.dump
```

Uložení souboru samo neověřuje obnovitelnost. Obnovu testovat do samostatné DB.
Před aktualizací uchovat i odpovídající commit a image ID.
Zastavení zachovávající data:

```bash
docker compose --env-file .env.preview -f compose.preview.yml down
```

Nepřidávat `-v`; neresetovat DB a automaticky nespouštět Alembic downgrade.
Při problému zastavit aplikaci, zachovat volume a zálohu, vrátit kompatibilní
image/commit. Pokud nový kód vyžaduje návrat schématu, nejprve schválit plán
obnovy a prokázat obnovitelnost zálohy; downgrade může mazat data.

## Přesné rozhraní pro VPS Codex

VPS workspace nebyl změněn. VPS Codex má nakonfigurovat **privátní** Tailscale
Serve / HTTPS reverse proxy na hostitelský `http://127.0.0.1:8088`.
Posílat celou cestu beze změny včetně `/api`; nginx už směruje `/api/*` do
FastAPI a ostatní cesty do statického frontendu. Při Caddy běžícím na hostiteli:

```caddyfile
# Uvnitř bloku pro zvolený privátní HTTPS hostname:
reverse_proxy 127.0.0.1:8088
```

Caddy v kontejneru nemá stejný localhost jako hostitel. Tam musí VPS Codex
navrhnout explicitní společnou proxy síť nebo odpovídající host networking;
nepřipojovat proxy k databázové síti a nepublikovat DB/backend.
Nesmí obejít nginx přímou routou na backend: tím by zpřístupnil starší zápisy.
Jestliže rozdělí routing, musí zachovat totožné blokování zápisů na všech API
včetně compatibility cest. Doporučená je jediná upstream adresa výše.

Ověřit ze vzdáleného prohlížeče na skutečné Tailscale HTTPS origin:
načtení homepage, přímý reload `/genes`, načtení JS/CSS,
GET `/api/health`, GET `/api/v1/genes`, hledání prázdné databáze bez
vymyšlených výsledků a odmítnutí POST/PATCH. Network panel musí ukázat
stejnou HTTPS origin a žádná volání na klientův localhost.
Bez existující Tailscale proxy a vzdáleného prohlížeče to nelze prohlásit za ověřené.

Žádné změny veřejné DNS, OpenStack pravidel nebo hlavního skrabana.com.
Před veřejným nasazením potvrdit e-INFRA group project nebo vhodné jiné VPS,
řešit autentizaci, zálohy, secrets a release politiku. Hlavní doména zůstává Webglobe.

## Provedené kontroly

- `docker compose config --quiet` pro development i samostatný preview: úspěch.
- Frontend: `corepack pnpm install --frozen-lockfile`, `format:check`, `lint`,
  `typecheck`, `test` (30/30) a build s `VITE_API_BASE_URL=/api/v1`: úspěch.
- Backend: instalace do ignorovaného `.venv`, Ruff lint/format a mypy: úspěch.
  První mypy běh před dokončením instalace selhal na chybějících knihovnách;
  po dokončení instalace prošel bez nálezů.
- `cd backend && ../.venv/bin/python -m pytest`: 54 prošlo, 3 PostgreSQL testy
  byly v tomto běhu záměrně přeskočeny bez testovací URL.
- Na samostatném dočasném PostgreSQL 17 kontejneru bez host portu, s daty
  v tmpfs, proběhlo všech šest migrací, `alembic check` bez rozdílů a všechny
  tři opt-in PostgreSQL testy úspěšně. Testovací URL byla předána jen v prostředí
  procesu jako `BKP_DATABASE_URL` a `BKP_TEST_POSTGRES_URL`; žádné testy
  neběžely proti stagingovým či existujícím VPS datům.

## Změněné a přidané soubory

- `compose.preview.yml`: samostatná staging topologie.
- `frontend/Dockerfile.preview`, `frontend/preview.conf`: produkční frontend build,
  SPA routing a proxy pro čtení API.
- `scripts/init-preview.py`: bezpečné vytvoření lokální konfigurace.
- `docker-compose.yml`: localhost HTTP bindings a DB bez host portu.
- `.dockerignore`, `frontend/.dockerignore`: vyloučení lokálních secrets.
- `README.md`, `ARCHITECTURE.md`, `CHANGELOG.md`, `docs/LOCAL_STAGING.md`: postup a záznam změn.

Lokálně vznikly ignorované `.env.preview`, `.venv`, `frontend/node_modules`
a `frontend/dist`. Dodaný nesledovaný `AGENTS.md` byl přečten a zachován.

## Výsledek lokálního spuštění

První Docker build a spuštění `bkp-local-preview` dokončeno úspěšně.
DB, backend a frontend jsou healthy; migrační služba skončila s kódem 0,
staging je na Alembic head `20261023_0006`.
Ověřené HTTP odpovědi přes `http://127.0.0.1:8088`:

- health 200 a status ok;
- homepage, přímé načtení `/genes` a odkazované JS/CSS soubory 200;
- šest entity listů a search 200 s prázdnými výsledky, bez demo importu;
- POST, PATCH a DELETE na API odmítnuty proxy kódem 403;
- neexistující API cesta vrací 404 a nepadá do SPA fallbacku.

Ověřen skutečný listener `127.0.0.1:8088` a Compose port bindings:
DB/backend bez publikovaného portu. Dočasný ověřovací PostgreSQL kontejner
byl zastaven a odstraněn; stagingové volume zůstává zachované.
První HTTP pokus během vytváření kontejnerů vrátil connection refused;
po dokončeném startu prošly všechny výše uvedené HTTP kontroly.
Vzdálený prohlížeč / Tailscale HTTPS nebyl ověřen. Lokální HTTP kontrola
neprokazuje funkčnost dosud nenakonfigurované vzdálené proxy.

Spuštěná sestava zůstává dostupná lokálně na VM. Při dalším použití stačí
`docker compose --env-file .env.preview -f compose.preview.yml up -d`.

## Navazující aktualizace fáze 8

Po samostatném předání infrastruktury se tato sestava stala upstreamem veřejného
dočasného studentského náhledu bkp.skrabana.com. Na výslovný pokyn uživatele byla
2026-11-07 aktualizována na 0.8.0, po záloze a ověřené obnově aktivních dat.
Aktuální postup a výsledky jsou v [záznamu nasazení](DEPLOYMENT_PHASE8.md).
Pro správu aktivní sestavy používat VPS scripts/bkp-preview.sh, který zachovává
restart override; původní příkazy výše zachycují první lokální spuštění.
Detaily opt-in workeru jsou v [Phase 8 operations](IMPORT_JOBS.md).
